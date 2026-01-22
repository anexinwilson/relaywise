data "aws_secretsmanager_secret" "app_secrets" {
  name = "cognive/lambda/secrets"
}