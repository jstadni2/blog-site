output "api_base_url" {
  description = "HTTP API invoke URL for the blog app."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "lambda_function_name" {
  description = "Deployed Lambda function name."
  value       = aws_lambda_function.app.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name used by the app."
  value       = aws_dynamodb_table.posts.name
}

output "ecr_repository_url" {
  description = "ECR repository URL containing the Lambda image."
  value       = aws_ecr_repository.app.repository_url
}
