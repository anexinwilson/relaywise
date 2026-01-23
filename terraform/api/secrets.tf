data "aws_secretsmanager_secret" "app_secrets" {
  name = "cognive/lambda/secrets"
}

data "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = data.aws_secretsmanager_secret.app_secrets.id
}