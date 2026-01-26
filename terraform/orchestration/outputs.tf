output "appsync_api_id" {
  value = aws_appsync_graphql_api.main.id
}

output "appsync_api_url" {
  value = aws_appsync_graphql_api.main.uris["GRAPHQL"]
}

output "events_api_id" {
  value = aws_cloudformation_stack.appsync_events.outputs["EventAPIId"]
}

output "events_api_key" {
  value     = aws_cloudformation_stack.appsync_events.outputs["ApiKey"]
  sensitive = true
}

output "events_websocket_endpoint" {
  value = aws_cloudformation_stack.appsync_events.outputs["WebSocketEndpoint"]
}

output "events_http_endpoint" {
  value = aws_cloudformation_stack.appsync_events.outputs["HttpEndpoint"]
}