resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "cognive/lambda/secrets"
  description             = "Runtime configuration for the Relaywise API, worker, and Clerk authorizer"
  recovery_window_in_days = 7
}
