output "appsync_api_id" {
  value = aws_appsync_graphql_api.main.id
}

output "appsync_api_url" {
  value = aws_appsync_graphql_api.main.uris["GRAPHQL"]
}

output "appsync_api_key" {
  value     = aws_appsync_api_key.main.key
  sensitive = true
}

