# Lambda execution role
resource "aws_iam_role" "lambda_role" {
  name = "cognive-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Lambda basic execution permissions
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda secrets manager access
resource "aws_iam_role_policy" "lambda_secrets_policy" {
  name = "lambda-secrets-policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.app_secrets.arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_queue_policy" {
  name = "lambda-agent-queue-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.agent_tasks.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "worker_runtime_policy" {
  name = "worker-runtime-policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource = aws_sqs_queue.agent_tasks.arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_ecr_policy" {
  name = "lambda-ecr-read-policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"]
      Resource = aws_ecr_repository.lambda_repo.arn
    }]
  })
}

# Authorizer execution role
resource "aws_iam_role" "authorizer_role" {
  name = "cognive-authorizer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Authorizer basic execution permissions
resource "aws_iam_role_policy_attachment" "authorizer_basic" {
  role       = aws_iam_role.authorizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Authorizer secrets manager access
resource "aws_iam_role_policy" "authorizer_secrets_policy" {
  name = "authorizer-secrets-policy"
  role = aws_iam_role.authorizer_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.app_secrets.arn
    }]
  })
}
