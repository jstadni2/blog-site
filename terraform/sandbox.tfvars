aws_region          = "us-east-2"
function_name       = "blog-site"
api_name            = "blog-site-http"
dynamodb_table_name = "blog_posts"
admin_username      = "admin"

tags = {
  Application = "blog-site"
  Environment = "sandbox"
  ManagedBy   = "terraform"
}
