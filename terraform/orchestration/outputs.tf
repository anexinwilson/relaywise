output "appsync_api_id" {
  value = aws_appsync_graphql_api.main.id
}

output "appsync_api_url" {
  value = aws_appsync_graphql_api.main.uris.GRAPHQL
}

output "appsync_api_key_secret_name" {
  value     = aws_secretsmanager_secret.appsync_api_key.name
  sensitive = false
}