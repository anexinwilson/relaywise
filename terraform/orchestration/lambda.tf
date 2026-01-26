data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_agentcore.py"
  output_path = "${path.module}/lambda_agentcore.zip"
}

resource "aws_iam_role" "agentcore_lambda_role" {
  name = "agentcore-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "agentcore_lambda_policy" {
  name = "agentcore-lambda-policy"
  role = aws_iam_role.agentcore_lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "agentcore_invoker" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "cognive-agentcore-invoker"
  role             = aws_iam_role.agentcore_lambda_role.arn
  handler          = "lambda_agentcore.lambda_handler"
  runtime          = "python3.11"
  timeout          = 900  # 15 minutes
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  environment {
    variables = {
      AGENTCORE_ENDPOINT = var.agentcore_endpoint
    }
  }
}

resource "aws_lambda_permission" "agentcore_appsync_invoke" {
  statement_id  = "AllowAppSyncInvokeAgentCore"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agentcore_invoker.function_name
  principal     = "appsync.amazonaws.com"
}

resource "aws_appsync_datasource" "agentcore_lambda" {
  api_id           = aws_appsync_graphql_api.main.id
  name             = "AgentCoreLambdaDataSource"
  type             = "AWS_LAMBDA"
  service_role_arn = aws_iam_role.appsync_lambda_role.arn
  
  lambda_config {
    function_arn = aws_lambda_function.agentcore_invoker.arn
  }
}
