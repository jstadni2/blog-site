# Blog Site

A minimal blog built with **Flask**, **Jinja2**, and **DynamoDB**. Posts are 
written in Markdown and stored in the database. An admin panel lets you
create, edit, publish, and delete posts.

## Features

- Public blog: post list and individual post pages with rendered Markdown
- Admin panel at `/admin/` (session-based login)
- Live Markdown preview while writing
- DynamoDB storage (AWS in production, local DynamoDB for development)
- Code syntax highlighting via Pygments
- Local DynamoDB support via Docker Compose

## Quick start

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start local DynamoDB (Docker Compose)
COMPOSE_DISABLE_ENV_FILE=1 docker compose up -d

# 4. Copy and configure environment variables
cp .env.example .env
#    Edit .env — at minimum set a proper SECRET_KEY.
#    Default dev credentials: admin / admin
#    FLASK_APP points to src.blogsite:app by default.

# 5. Initialize the DynamoDB table
FLASK_APP=src.blogsite:app flask init-db

# 6. Run the dev server
FLASK_APP=src.blogsite:app flask run
```

Open <http://127.0.0.1:5000> in your browser.

The admin panel is at <http://127.0.0.1:5000/admin/login>.

## Changing the admin password

Generate a hash for your password and put it in `.env` as `ADMIN_PASSWORD_HASH`:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpassword'))"
```

## Project layout

```
blog-site/
├── src/
│   └── blogsite/
│       ├── app.py          # Flask application
│       ├── static/
│       │   ├── css/
│       │   │   ├── style.css
│       │   │   └── editor.css
│       │   └── js/
│       │       └── editor.js   # Live Markdown preview (uses marked.js CDN)
│       └── templates/
│           ├── base.html
│           ├── index.html
│           ├── post.html
│           ├── 404.html
│           └── admin/
│               ├── login.html
│               ├── dashboard.html
│               ├── new_post.html
│               └── edit_post.html
├── requirements.txt
├── .env.example
├── docker-compose.yml      # Local DynamoDB service
└── tests/
```

## Production notes

- Set `SECRET_KEY` to a cryptographically random value (`python -c "import secrets; print(secrets.token_hex(32))"`)
- Set `ADMIN_PASSWORD_HASH` to a proper hashed password
- Set `DYNAMODB_TABLE_NAME` to your target table name
- Remove `DYNAMODB_ENDPOINT_URL` in production so boto3 uses AWS endpoints
- Use AWS IAM credentials/role with access to the DynamoDB table
- Run behind a WSGI server (e.g. Gunicorn) with HTTPS
