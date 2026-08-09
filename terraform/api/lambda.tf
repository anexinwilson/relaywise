resource "aws_ecr_repository" "lambda_repo" {
  name                 = "cognive-lambda-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "lambda_repo" {
  repository = aws_ecr_repository.lambda_repo.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the ten most recent Cognive Lambda images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_sqs_queue" "agent_tasks_dlq" {
  name                      = "relaywise-agent-tasks-dlq.fifo"
  fifo_queue                = true
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "agent_tasks" {
  name                        = "relaywise-agent-tasks.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  visibility_timeout_seconds  = 900
  message_retention_seconds   = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agent_tasks_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_cloudwatch_log_group" "authorizer_logs" {
  name              = "/aws/lambda/cognive-authorizer"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "cognive_lambda_logs" {
  name              = "/aws/lambda/cognive-lambda"
  retention_in_days = 7
}

resource "aws_lambda_function" "authorizer" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "cognive-authorizer"
  role          = aws_iam_role.authorizer_role.arn
  timeout       = 30

  image_uri    = var.authorizer_image_uri
  package_type = "Image"

  logging_config {
    log_group  = aws_cloudwatch_log_group.authorizer_logs.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.authorizer_logs,
    aws_iam_role_policy_attachment.authorizer_basic,
  ]

  lifecycle {
    precondition {
      condition     = var.authorizer_image_uri != null && can(regex("@sha256:[0-9a-f]{64}$", var.authorizer_image_uri))
      error_message = "authorizer_image_uri must be a digest-pinned ECR URI when deployment_phase is complete."
    }
  }
}

resource "aws_cloudwatch_log_group" "worker_logs" {
  name              = "/aws/lambda/relaywise-agent-worker"
  retention_in_days = 7
}

resource "aws_lambda_function" "cognive_lambda" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "cognive-lambda"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 120
  memory_size   = 512

  image_uri    = var.lambda_image_uri
  package_type = "Image"

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_ID = aws_secretsmanager_secret.app_secrets.name
      COMPOSIO_CACHE_DIR       = "/tmp/composio"
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.cognive_lambda_logs.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.cognive_lambda_logs,
    aws_iam_role_policy_attachment.lambda_basic,
  ]

  lifecycle {
    precondition {
      condition     = var.lambda_image_uri != null && can(regex("@sha256:[0-9a-f]{64}$", var.lambda_image_uri))
      error_message = "lambda_image_uri must be a digest-pinned ECR URI when deployment_phase is complete."
    }
  }
}

resource "aws_lambda_function" "agent_worker" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "relaywise-agent-worker"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 900
  memory_size   = 1024
  image_uri     = var.worker_image_uri
  package_type  = "Image"

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_ID = aws_secretsmanager_secret.app_secrets.name
      COMPOSIO_CACHE_DIR       = "/tmp/composio"
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.worker_logs.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.worker_logs,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.worker_runtime_policy,
    aws_iam_role_policy.lambda_ecr_policy,
  ]

  lifecycle {
    precondition {
      condition     = var.worker_image_uri != null && can(regex("@sha256:[0-9a-f]{64}$", var.worker_image_uri))
      error_message = "worker_image_uri must be a digest-pinned ECR URI when deployment_phase is complete."
    }
  }
}

resource "aws_lambda_event_source_mapping" "agent_tasks" {
  count                   = var.deployment_phase == "complete" ? 1 : 0
  event_source_arn        = aws_sqs_queue.agent_tasks.arn
  function_name           = aws_lambda_function.agent_worker[0].arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
  scaling_config { maximum_concurrency = 2 }
}
