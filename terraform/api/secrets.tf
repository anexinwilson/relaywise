resource "aws_secretsmanager_secret" "app_secrets" {
  name = "cognive/lambda/secrets"
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    DATABASE_URL             = ""
    UPSTASH_REDIS_REST_URL   = ""
    UPSTASH_REDIS_REST_TOKEN = ""
    CLERK_SECRET_KEY         = ""
    CLERK_WEBHOOK_SECRET     = ""
    CLERK_DOMAIN             = ""
    AWS_REGION               = ""
    AGENTCORE_MEMORY_ID      = ""
  })
}