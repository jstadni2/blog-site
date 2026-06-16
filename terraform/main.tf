data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

resource "aws_dynamodb_table" "posts" {
  name         = local.full_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "slug"
    type = "S"
  }

  global_secondary_index {
    name            = "slug-index"
    hash_key        = "slug"
    projection_type = "ALL"
  }

  tags = merge(local.effective_tags, {
    Name = local.full_table_name
  })
}

resource "aws_ecr_repository" "app" {
  name                 = local.full_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.effective_tags, {
    Name = local.full_repository_name
  })
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain only the 10 most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "null_resource" "docker_build_push" {
  triggers = {
    source_hash    = local.image_source_hash
    repository_url = aws_ecr_repository.app.repository_url
    image_tag      = var.image_tag
    aws_region     = var.aws_region
  }

  provisioner "local-exec" {
    command     = <<-EOT
      set -euo pipefail
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}
      docker build --platform linux/amd64 -f ${path.module}/Dockerfile.lambda -t ${aws_ecr_repository.app.repository_url}:${var.image_tag} ${local.project_root}
      docker push ${aws_ecr_repository.app.repository_url}:${var.image_tag}
    EOT
    interpreter = ["/bin/bash", "-c"]
  }

  depends_on = [aws_ecr_repository.app]
}

resource "aws_iam_role" "lambda_exec" {
  name = "${local.full_function_name}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.effective_tags, {
    Name = "${local.full_function_name}-lambda-exec"
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.full_function_name}-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DescribeTable",
          "dynamodb:CreateTable"
        ]
        Resource = [
          aws_dynamodb_table.posts.arn,
          "${aws_dynamodb_table.posts.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.full_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.effective_tags, {
    Name = "/aws/lambda/${local.full_function_name}"
  })
}

resource "aws_lambda_function" "app" {
  function_name = local.full_function_name
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  architectures = ["x86_64"]

  environment {
    variables = {
      SECRET_KEY          = var.secret_key
      ADMIN_USERNAME      = var.admin_username
      ADMIN_PASSWORD_HASH = var.admin_password_hash
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.posts.name
      AWS_DEFAULT_REGION  = data.aws_region.current.name
    }
  }

  depends_on = [
    null_resource.docker_build_push,
    aws_cloudwatch_log_group.lambda
  ]

  tags = merge(local.effective_tags, {
    Name = local.full_function_name
  })
}

resource "aws_apigatewayv2_api" "http" {
  name          = local.full_api_name
  protocol_type = "HTTP"

  tags = merge(local.effective_tags, {
    Name = local.full_api_name
  })
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  tags = merge(local.effective_tags, {
    Name = "${local.full_api_name}-default"
  })
}

resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
