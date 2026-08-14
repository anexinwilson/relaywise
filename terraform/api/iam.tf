locals {
  lambda_assume_role = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# One role per function. A shared role gave the API queue-consume rights it
# never uses and the worker queue-produce rights it never uses.

# --- API resolver Lambda -----------------------------------------------------

resource "aws_iam_role" "api" {
  name               = "relaywise-api-role"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "api_basic" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "api_runtime" {
  name = "relaywise-api-runtime"
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.app_secrets.arn
      },
      {
        # Produce only. The API never consumes from the queue.
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.agent_tasks.arn
      },
    ]
  })
}

# --- Agent worker Lambda -----------------------------------------------------

resource "aws_iam_role" "worker" {
  name               = "relaywise-worker-role"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "worker_basic" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "worker_runtime" {
  name = "relaywise-worker-runtime"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.app_secrets.arn
      },
      {
        # Consume only. The worker never enqueues.
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
        ]
        Resource = aws_sqs_queue.agent_tasks.arn
      },
    ]
  })
}

# --- Clerk authorizer Lambda -------------------------------------------------

resource "aws_iam_role" "authorizer" {
  name               = "relaywise-authorizer-role"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "authorizer_basic" {
  role       = aws_iam_role.authorizer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "authorizer_secrets" {
  name = "relaywise-authorizer-secrets"
  role = aws_iam_role.authorizer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.app_secrets.arn
    }]
  })
}

# --- Control-plane Lambda ----------------------------------------------------
# Reaches Composio and Redis over the internet; needs no AWS data plane access
# beyond reading the secret.

resource "aws_iam_role" "integrations" {
  name               = "relaywise-integrations-role"
  assume_role_policy = local.lambda_assume_role
}

resource "aws_iam_role_policy_attachment" "integrations_basic" {
  role       = aws_iam_role.integrations.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "integrations_runtime" {
  name = "relaywise-integrations-runtime"
  role = aws_iam_role.integrations.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.app_secrets.arn
    }]
  })
}
