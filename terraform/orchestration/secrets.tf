resource "aws_secretsmanager_secret" "appsync_api_key" {
  name = "cognive/appsync/api-key"
}