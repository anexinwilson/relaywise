# Lambda execution role
resource "aws_iam_role" "lambda_role" {
  name = "cognive-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
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
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:cognive/lambda/secrets-*"
    }]
  })
}

# Lambda policy to invoke AgentCore Runtime
resource "aws_iam_role_policy" "lambda_agentcore_policy" {
  name = "lambda-agentcore-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntimeForUser",
          "bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream",
          "bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStreamForUser",
          "bedrock-agentcore:StopRuntimeSession"
        ]
        Resource = "arn:aws:bedrock-agentcore:${var.aws_region}:*:runtime/*"
      }
    ]
  })
}

# Lambda policy to access AgentCore Memory
resource "aws_iam_role_policy" "lambda_agentcore_memory_policy" {
  name = "lambda-agentcore-memory-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:ListSessions",
          "bedrock-agentcore:ListEvents",
          "bedrock-agentcore:CreateEvent",
          "bedrock-agentcore:GetMemory",
          "bedrock-agentcore:RetrieveMemory"
        ]
        Resource = "arn:aws:bedrock-agentcore:${var.aws_region}:*:memory/*"
      }
    ]
  })
}

# Authorizer execution role
resource "aws_iam_role" "authorizer_role" {
  name = "cognive-authorizer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
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
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:cognive/lambda/secrets-*"
    }]
  })
}