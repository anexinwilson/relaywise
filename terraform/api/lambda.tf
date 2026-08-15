locals {
  # Visibility must exceed the worker timeout, or a slow run can be redelivered
  # while the first attempt is still executing.
  worker_timeout_seconds   = 300
  queue_visibility_seconds = 360
  # Per image type, not in total.
  retained_container_images = 5
}

# --- Container registry ------------------------------------------------------

resource "aws_ecr_repository" "lambda_repo" {
  name = "relaywise-lambda-repo"

  # Deploys are digest-pinned, so tags never need to be overwritten. IMMUTABLE
  # makes that policy structural rather than a convention.
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "lambda_repo" {
  repository = aws_ecr_repository.lambda_repo.name

  # One repository holds three different images, distinguished by tag prefix.
  # A single "keep N most recent" rule counts them together, so a run of worker
  # pushes silently expired the api and authorizer images and their Lambdas
  # could no longer start. Retention has to be per image type.
  policy = jsonencode({
    rules = concat(
      [
        for index, prefix in ["api", "authorizer", "worker"] : {
          rulePriority = index + 1
          description  = "Keep the ${local.retained_container_images} most recent ${prefix} images"
          selection = {
            tagStatus     = "tagged"
            tagPrefixList = ["${prefix}-"]
            countType     = "imageCountMoreThan"
            countNumber   = local.retained_container_images
          }
          action = { type = "expire" }
        }
      ],
      [{
        rulePriority = 10
        description  = "Expire untagged layers left behind by a failed push"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      }]
    )
  })
}

# --- Task queue --------------------------------------------------------------

resource "aws_sqs_queue" "agent_tasks_dlq" {
  name                      = "relaywise-agent-tasks-dlq.fifo"
  fifo_queue                = true
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "agent_tasks" {
  name       = "relaywise-agent-tasks.fifo"
  fifo_queue = true

  # Deduplication is explicit per message: two identical prompts in the same
  # conversation are legitimate and must not be collapsed.
  content_based_deduplication = false

  visibility_timeout_seconds = local.queue_visibility_seconds
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agent_tasks_dlq.arn
    maxReceiveCount     = 3
  })
}

# --- Log groups --------------------------------------------------------------
# Declared explicitly so retention is set; Lambda would otherwise create them
# with never-expire retention on first invocation.

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/relaywise-api"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "authorizer" {
  name              = "/aws/lambda/relaywise-authorizer"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/relaywise-agent-worker"
  retention_in_days = 7
}

# --- Functions ---------------------------------------------------------------

resource "aws_lambda_function" "api" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "relaywise-api"
  role          = aws_iam_role.api.arn
  timeout       = 30 # AppSync gives up at 30s; no point outliving the caller
  memory_size   = 512

  image_uri    = var.lambda_image_uri
  package_type = "Image"

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_ID = aws_secretsmanager_secret.app_secrets.name
      CORS_ALLOWED_ORIGINS      = var.cors_allowed_origins
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.api.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy_attachment.api_basic,
    aws_iam_role_policy.api_runtime,
  ]

  lifecycle {
    precondition {
      condition     = var.lambda_image_uri != null && can(regex("@sha256:[0-9a-f]{64}$", var.lambda_image_uri))
      error_message = "lambda_image_uri must be a digest-pinned ECR URI when deployment_phase is complete."
    }
  }
}

resource "aws_lambda_function" "authorizer" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "relaywise-authorizer"
  role          = aws_iam_role.authorizer.arn
  timeout       = 10

  image_uri    = var.authorizer_image_uri
  package_type = "Image"

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_ID = aws_secretsmanager_secret.app_secrets.name
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.authorizer.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.authorizer,
    aws_iam_role_policy_attachment.authorizer_basic,
    aws_iam_role_policy.authorizer_secrets,
  ]

  lifecycle {
    precondition {
      condition     = var.authorizer_image_uri != null && can(regex("@sha256:[0-9a-f]{64}$", var.authorizer_image_uri))
      error_message = "authorizer_image_uri must be a digest-pinned ECR URI when deployment_phase is complete."
    }
  }
}

resource "aws_lambda_function" "agent_worker" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "relaywise-agent-worker"
  role          = aws_iam_role.worker.arn
  timeout       = local.worker_timeout_seconds

  # 1024 MB against a measured peak of ~305 MB, so headroom is roughly 3x.
  #
  # This was 2048 for one reason: Lambda caps init at 10s whatever the function
  # timeout is, importing LangGraph and Composio at module scope exceeded it,
  # and memory buys CPU. That is no longer how the worker starts. The imports
  # are lazy now (see worker/handler.py), so they run in the invoke phase where
  # no ceiling applies and a slower import costs seconds instead of a timeout.
  #
  # Dropping back is a real saving rather than a wash. Billing is GB-ms, and a
  # healthy run spends 4 to 12 seconds mostly waiting on Bedrock, Composio and
  # Postgres. Waiting does not get faster with more CPU, so the second gigabyte
  # was being charged for idle time.
  #
  # Ignore the 40 to 52 second runs in the old logs when sizing this. Those
  # were a run thrashing against a since-removed model call ceiling, and a cold
  # start where init timed out and Lambda repeated the whole initialization.
  # Neither is what the work actually costs.
  memory_size = 1024

  image_uri    = var.worker_image_uri
  package_type = "Image"

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_ID = aws_secretsmanager_secret.app_secrets.name
      COMPOSIO_CACHE_DIR        = "/tmp/composio"
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.worker.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.worker,
    aws_iam_role_policy_attachment.worker_basic,
    aws_iam_role_policy.worker_runtime,
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

  scaling_config {
    maximum_concurrency = var.worker_max_concurrency
  }
}

# --- Connected-app control plane ---------------------------------------------
# Built from the *worker* image with an overridden entrypoint. Same artefact,
# different CMD: the Composio SDK stays out of the API Lambda that serves
# conversation queries, and there is no third image to build.

resource "aws_cloudwatch_log_group" "integrations" {
  name              = "/aws/lambda/relaywise-integrations"
  retention_in_days = 7
}

resource "aws_lambda_function" "integrations" {
  count         = var.deployment_phase == "complete" ? 1 : 0
  function_name = "relaywise-integrations"
  role          = aws_iam_role.integrations.arn
  timeout       = 30 # AppSync gives up at 30s
  memory_size   = 1024

  image_uri    = var.worker_image_uri
  package_type = "Image"

  image_config {
    command = ["integrations.handler.handler"]
  }

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_ID = aws_secretsmanager_secret.app_secrets.name
      COMPOSIO_CACHE_DIR        = "/tmp/composio"
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.integrations.name
    log_format = "JSON"
  }

  depends_on = [
    aws_cloudwatch_log_group.integrations,
    aws_iam_role_policy_attachment.integrations_basic,
    aws_iam_role_policy.integrations_runtime,
  ]

  lifecycle {
    precondition {
      condition     = var.worker_image_uri != null && can(regex("@sha256:[0-9a-f]{64}$", var.worker_image_uri))
      error_message = "worker_image_uri must be a digest-pinned ECR URI when deployment_phase is complete."
    }
  }
}
