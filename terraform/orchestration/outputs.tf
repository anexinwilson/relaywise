output "appsync_api_id" {
  description = "Cognive AppSync GraphQL API ID"
  value       = aws_appsync_graphql_api.main.id
}

output "appsync_api_url" {
  description = "Cognive AppSync GraphQL API URL (endpoint for GraphQL queries)"
  value       = aws_appsync_graphql_api.main.uris.GRAPHQL
}

output "appsync_api_key" {
  description = "Cognive AppSync GraphQL API Key (use in x-api-key header for authentication)"
  value       = aws_appsync_api_key.main.key
  sensitive   = true
}

output "appsync_api_arn" {
  description = "Cognive AppSync GraphQL API ARN (Amazon Resource Name)"
  value       = aws_appsync_graphql_api.main.arn
}