variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-2"
}

variable "name_prefix" {
  description = "Optional username/environment prefix for resource naming."
  type        = string
  default     = ""
}

variable "function_name" {
  description = "Base Lambda function name (prefix will be added when set)."
  type        = string
  default     = "blog-site"
}

variable "api_name" {
  description = "Base API Gateway HTTP API name (prefix will be added when set)."
  type        = string
  default     = "blog-site-http"
}

variable "dynamodb_table_name" {
  description = "Base DynamoDB table name (prefix will be added when set)."
  type        = string
  default     = "blog_posts"
}

variable "secret_key" {
  description = "Flask SECRET_KEY value injected into Lambda environment."
  type        = string
  sensitive   = true
}

variable "admin_username" {
  description = "Admin username for the app."
  type        = string
  default     = "admin"
}

variable "admin_password_hash" {
  description = "Optional Werkzeug password hash for admin login."
  type        = string
  default     = ""
  sensitive   = true
}

variable "image_tag" {
  description = "Container image tag to push to ECR and deploy to Lambda."
  type        = string
  default     = "latest"
}

variable "lambda_memory_size" {
  description = "Lambda memory in MB."
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "CloudWatch log retention for Lambda logs."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Additional tags applied to resources."
  type        = map(string)
  default     = {}
}
