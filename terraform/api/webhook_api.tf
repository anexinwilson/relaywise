resource "aws_apigatewayv2_api" "webhooks" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  name          = "relaywise-webhooks"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "webhooks" {
  count                  = var.deployment_phase == "complete" ? 1 : 0
  api_id                 = aws_apigatewayv2_api.webhooks[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.cognive_lambda[0].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "composio_webhook" {
  count     = var.deployment_phase == "complete" ? 1 : 0
  api_id    = aws_apigatewayv2_api.webhooks[0].id
  route_key = "POST /webhooks/composio"
  target    = "integrations/${aws_apigatewayv2_integration.webhooks[0].id}"
}

resource "aws_apigatewayv2_stage" "webhooks" {
  count       = var.deployment_phase == "complete" ? 1 : 0
  api_id      = aws_apigatewayv2_api.webhooks[0].id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "webhook_api" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  statement_id  = "AllowWebhookApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognive_lambda[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhooks[0].execution_arn}/*/*"
}
