resource "aws_ecr_repository" "lambda_repo" {
  name                 = "cognive-lambda-repo"
  image_tag_mutability = "MUTABLE"
}

resource "aws_cloudwatch_log_group" "authorizer_logs" {
  name              = "/aws/lambda/cognive-authorizer"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "token_manager_logs" {
  name              = "/aws/lambda/cognive-token-manager"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "cognive_lambda_logs" {
  name              = "/aws/lambda/cognive-lambda"
  retention_in_days = 7
}

resource "aws_lambda_function" "authorizer" {
  function_name = "cognive-authorizer"
  role          = aws_iam_role.authorizer_role.arn
  timeout       = 30

  image_uri    = "${aws_ecr_repository.lambda_repo.repository_url}:cognive-authorizer"
  package_type = "Image"

  logging_config {
    log_group  = aws_cloudwatch_log_group.authorizer_logs.name
    log_format = "JSON"
  }

  depends_on = [aws_cloudwatch_log_group.authorizer_logs]
}

resource "aws_lambda_function" "cognive_lambda" {
  function_name = "cognive-lambda"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 120
  memory_size   = 512

  image_uri    = "${aws_ecr_repository.lambda_repo.repository_url}:cognive-lambda"
  package_type = "Image"

  logging_config {
    log_group  = aws_cloudwatch_log_group.cognive_lambda_logs.name
    log_format = "JSON"
  }

  depends_on = [aws_cloudwatch_log_group.cognive_lambda_logs]
}

resource "aws_lambda_function_url" "cognive_lambda_url" {
  function_name      = aws_lambda_function.cognive_lambda.function_name
  authorization_type = "NONE"
  
  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["*"]
  }
}

resource "aws_lambda_permission" "cognive_lambda_url_permission" {
  statement_id           = "AllowPublicInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.cognive_lambda.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function" "token_manager" {
  function_name = "cognive-token-manager"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 30

  image_uri    = "${aws_ecr_repository.lambda_repo.repository_url}:cognive-token-manager"
  package_type = "Image"

  logging_config {
    log_group  = aws_cloudwatch_log_group.token_manager_logs.name
    log_format = "JSON"
  }

  depends_on = [aws_cloudwatch_log_group.token_manager_logs]
}

resource "aws_lambda_function_url" "token_manager_url" {
  function_name          = aws_lambda_function.token_manager.function_name
  authorization_type     = "NONE"
  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["Content-Type"]
  }
}

resource "aws_lambda_permission" "token_manager_url_permission" {
  statement_id           = "AllowPublicInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.token_manager.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}