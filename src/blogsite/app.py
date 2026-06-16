import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

import boto3
import markdown as md
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from boto3.dynamodb.conditions import Attr, Key
from slugify import slugify
from botocore.exceptions import ClientError
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.permanent_session_lifetime = timedelta(hours=8)

# Admin credentials — set via environment variables in production.
# Default dev credentials: username=admin  password=admin
ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
_raw_hash = os.environ.get("ADMIN_PASSWORD_HASH")
ADMIN_PASSWORD_HASH: str = _raw_hash if _raw_hash else generate_password_hash("admin")

# DynamoDB configuration
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "blog_posts")
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL")
DYNAMODB_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Helpful defaults for local DynamoDB usage only.
if DYNAMODB_ENDPOINT_URL:
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "local")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "local")

# ---------------------------------------------------------------------------
# DynamoDB repository
# ---------------------------------------------------------------------------


def _parse_created_at(created_raw: str | datetime | None) -> datetime:
    if isinstance(created_raw, datetime):
        return created_raw
    if isinstance(created_raw, str):
        try:
            return datetime.fromisoformat(created_raw)
        except ValueError:
            return datetime.utcnow()
    return datetime.utcnow()


class PostRepository:
    def __init__(self) -> None:
        self._dynamodb = boto3.resource(
            "dynamodb",
            region_name=DYNAMODB_REGION,
            endpoint_url=DYNAMODB_ENDPOINT_URL,
        )
        self._table = self._dynamodb.Table(DYNAMODB_TABLE_NAME)

    def ensure_table(self) -> None:
        try:
            self._table.load()
        except ClientError as exc:
            err = exc.response.get("Error", {}).get("Code", "")
            if err != "ResourceNotFoundException":
                raise

            self._dynamodb.create_table(
                TableName=DYNAMODB_TABLE_NAME,
                KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "id", "AttributeType": "S"},
                    {"AttributeName": "slug", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "slug-index",
                        "KeySchema": [
                            {"AttributeName": "slug", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._table.wait_until_exists()

    def _to_template_post(self, item: dict) -> dict:
        created_val = _parse_created_at(item.get("created_at"))
        return {
            "id": item["id"],
            "title": item["title"],
            "slug": item["slug"],
            "content": item.get("content", ""),
            "published": int(item.get("published", 0)),
            "created_at": created_val,
            "updated_at": item.get("updated_at"),
        }

    def list_posts(self, published_only: bool = False) -> list[dict]:
        if published_only:
            response = self._table.scan(FilterExpression=Attr("published").eq(1))
        else:
            response = self._table.scan()
        items = [self._to_template_post(item) for item in response.get("Items", [])]
        items.sort(key=lambda post: post.get("created_at", datetime.utcnow()), reverse=True)
        return items

    def get_post_by_slug(self, slug: str, published_only: bool = False) -> dict | None:
        response = self._table.query(
            IndexName="slug-index",
            KeyConditionExpression=Key("slug").eq(slug),
        )
        for item in response.get("Items", []):
            post = self._to_template_post(item)
            if not published_only or post["published"] == 1:
                return post
        return None

    def get_post_by_id(self, post_id: str) -> dict | None:
        response = self._table.get_item(Key={"id": post_id})
        item = response.get("Item")
        return self._to_template_post(item) if item else None

    def slug_exists(self, slug: str, exclude_id: str | None = None) -> bool:
        response = self._table.query(
            IndexName="slug-index",
            KeyConditionExpression=Key("slug").eq(slug),
        )
        for item in response.get("Items", []):
            if exclude_id is None or item.get("id") != exclude_id:
                return True
        return False

    def create_post(self, title: str, slug: str, content: str, published: int) -> str:
        post_id = str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat()
        self._table.put_item(
            Item={
                "id": post_id,
                "title": title,
                "slug": slug,
                "content": content,
                "published": int(published),
                "created_at": now_str,
                "updated_at": now_str,
            }
        )
        return post_id

    def update_post(self, post_id: str, title: str, content: str, published: int) -> None:
        now_str = datetime.utcnow().isoformat()
        self._table.update_item(
            Key={"id": post_id},
            UpdateExpression=(
                "SET title = :title, content = :content, "
                "published = :published, updated_at = :updated_at"
            ),
            ExpressionAttributeValues={
                ":title": title,
                ":content": content,
                ":published": int(published),
                ":updated_at": now_str,
            },
        )

    def delete_post(self, post_id: str) -> None:
        self._table.delete_item(Key={"id": post_id})


repo = PostRepository()


@app.teardown_appcontext
def close_db(error: Exception | None) -> None:
    return


def init_db() -> None:
    repo.ensure_table()


@app.cli.command("init-db")
def init_db_command() -> None:
    """Initialise the DynamoDB table."""
    init_db()
    print("DynamoDB table initialised.")


@app.before_request
def ensure_db() -> None:
    if os.environ.get("DYNAMODB_AUTO_INIT"):
        init_db()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def login_required(f):  # type: ignore[type-arg]
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(content: str) -> str:
    return md.markdown(
        content,
        extensions=["fenced_code", "tables", "toc", "codehilite", "nl2br"],
    )


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    posts = repo.list_posts(published_only=True)
    return render_template("index.html", posts=posts)


@app.route("/post/<slug>")
def post(slug: str):
    row = repo.get_post_by_slug(slug, published_only=True)
    if row is None:
        abort(404)
    html_content = render_markdown(row.get("content", ""))
    return render_template("post.html", post=row, content=html_content)


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(
            ADMIN_PASSWORD_HASH, password
        ):
            session.clear()
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid username or password."

    return render_template("admin/login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/")
@login_required
def admin_dashboard():
    posts = repo.list_posts(published_only=False)
    return render_template("admin/dashboard.html", posts=posts)


@app.route("/admin/new", methods=["GET", "POST"])
@login_required
def admin_new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        published = 1 if request.form.get("published") else 0

        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            slug = slugify(title)
            base_slug, i = slug, 1
            while repo.slug_exists(slug):
                slug = f"{base_slug}-{i}"
                i += 1

            repo.create_post(title, slug, content, published)
            flash("Post created successfully.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/new_post.html", post=None)


@app.route("/admin/edit/<post_id>", methods=["GET", "POST"])
@login_required
def admin_edit_post(post_id: str):
    post = repo.get_post_by_id(post_id)
    if post is None:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        published = 1 if request.form.get("published") else 0

        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            repo.update_post(post_id, title, content, published)
            flash("Post updated successfully.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/edit_post.html", post=post)


@app.route("/admin/delete/<post_id>", methods=["POST"])
@login_required
def admin_delete_post(post_id: str):
    repo.delete_post(post_id)
    flash("Post deleted.", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
