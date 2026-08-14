output "api_function_arn" {
  description = "Pass to terraform/orchestration as lambda_function_arn."
  value       = try(aws_lambda_function.api[0].arn, null)
}

output "authorizer_function_arn" {
  description = "Pass to terraform/orchestration as authorizer_function_arn."
  value       = try(aws_lambda_function.authorizer[0].arn, null)
}

output "worker_function_arn" {
  value = try(aws_lambda_function.agent_worker[0].arn, null)
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda_repo.repository_url
}

output "lambda_secret_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}

output "agent_queue_url" {
  description = "Set as SQS_QUEUE_URL in the secret."
  value       = aws_sqs_queue.agent_tasks.url
}

output "agent_queue_dlq_url" {
  value = aws_sqs_queue.agent_tasks_dlq.url
}

output "composio_webhook_url" {
  description = <<-EOT
    Register this in the Composio dashboard as the webhook endpoint.

    This is NOT the OAuth callback: Composio redirects the user's browser to
    `CALLBACK_URL` after consent, and that must be a frontend page.
  EOT
  value       = try("${trim(aws_apigatewayv2_stage.webhooks[0].invoke_url, "/")}/webhooks/composio", null)
}

output "integrations_function_arn" {
  description = "Pass to terraform/orchestration as integrations_function_arn."
  value       = try(aws_lambda_function.integrations[0].arn, null)
}
