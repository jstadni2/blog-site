aws_region          = "us-east-2"
function_name       = "blog-site"
api_name            = "blog-site-http"
dynamodb_table_name = "blog_posts"
admin_username      = "admin"

# Optional: set a generated hash, or leave empty to use app fallback behavior.
# Example:
# python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('change-me'))"
admin_password_hash = ""

tags = {
  Application = "blog-site"
  Environment = "sandbox"
  ManagedBy   = "terraform"
}
