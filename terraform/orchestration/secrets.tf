resource "aws_secretsmanager_secret" "appsync_api_key" {
  name = "cognive/appsync/api-key"
}

resource "aws_secretsmanager_secret_version" "appsync_api_key" {
  secret_id     = aws_secretsmanager_secret.appsync_api_key.id
  secret_string = aws_appsync_api_key.main.key
}

data "aws_secretsmanager_secret_version" "lambda_arn_secret" {
  secret_id = "cognive/lambda/arn"
}

locals {
  lambda_function_arn = jsondecode(data.aws_secretsmanager_secret_version.lambda_arn_secret.secret_string)["lambda_arn"]
}