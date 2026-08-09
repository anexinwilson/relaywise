output "lambda_function_arn" {
  value = try(aws_lambda_function.cognive_lambda[0].arn, null)
}

output "worker_function_arn" {
  value = try(aws_lambda_function.agent_worker[0].arn, null)
}

output "authorizer_function_arn" {
  value = try(aws_lambda_function.authorizer[0].arn, null)
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda_repo.repository_url
}

output "lambda_secret_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}

output "agent_queue_url" {
  value = aws_sqs_queue.agent_tasks.url
}

output "agent_queue_dlq_url" {
  value = aws_sqs_queue.agent_tasks_dlq.url
}

output "composio_callback_url" {
  value = try("${trim(aws_apigatewayv2_stage.webhooks[0].invoke_url, "/")}/webhooks/composio", null)
}
