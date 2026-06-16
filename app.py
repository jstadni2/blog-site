import os
import sqlite3
from datetime import timedelta
from functools import wraps

import markdown as md
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from slugify import slugify
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.permanent_session_lifetime = timedelta(hours=8)

DATABASE = os.path.join(app.instance_path, "blog.db")

# Admin credentials — set via environment variables in production.
# Default dev credentials: username=admin  password=admin
ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
_raw_hash = os.environ.get("ADMIN_PASSWORD_HASH")
ADMIN_PASSWORD_HASH: str = _raw_hash if _raw_hash else generate_password_hash("admin")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        os.makedirs(app.instance_path, exist_ok=True)
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            slug        TEXT    NOT NULL UNIQUE,
            content     TEXT    NOT NULL,
            published   INTEGER NOT NULL DEFAULT 1,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()


@app.cli.command("init-db")
def init_db_command() -> None:
    """Initialise the SQLite database."""
    init_db()
    print("Database initialised.")


@app.before_request
def ensure_db() -> None:
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
    db = get_db()
    posts = db.execute(
        "SELECT id, title, slug, created_at FROM posts"
        " WHERE published = 1 ORDER BY created_at DESC"
    ).fetchall()
    return render_template("index.html", posts=posts)


@app.route("/post/<slug>")
def post(slug: str):
    db = get_db()
    row = db.execute(
        "SELECT * FROM posts WHERE slug = ? AND published = 1", (slug,)
    ).fetchone()
    if row is None:
        abort(404)
    html_content = render_markdown(row["content"])
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
    db = get_db()
    posts = db.execute(
        "SELECT id, title, slug, published, created_at FROM posts ORDER BY created_at DESC"
    ).fetchall()
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
            db = get_db()
            slug = slugify(title)
            base_slug, i = slug, 1
            while db.execute(
                "SELECT id FROM posts WHERE slug = ?", (slug,)
            ).fetchone():
                slug = f"{base_slug}-{i}"
                i += 1

            db.execute(
                "INSERT INTO posts (title, slug, content, published) VALUES (?, ?, ?, ?)",
                (title, slug, content, published),
            )
            db.commit()
            flash("Post created successfully.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/new_post.html", post=None)


@app.route("/admin/edit/<int:post_id>", methods=["GET", "POST"])
@login_required
def admin_edit_post(post_id: int):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post is None:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        published = 1 if request.form.get("published") else 0

        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            db.execute(
                "UPDATE posts SET title = ?, content = ?, published = ?,"
                " updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, content, published, post_id),
            )
            db.commit()
            flash("Post updated successfully.", "success")
            return redirect(url_for("admin_dashboard"))

    return render_template("admin/edit_post.html", post=post)


@app.route("/admin/delete/<int:post_id>", methods=["POST"])
@login_required
def admin_delete_post(post_id: int):
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
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
