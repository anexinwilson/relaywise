resource "aws_ecr_repository" "lambda_repo" {
  name                 = "cognive-lambda-repo"
  image_tag_mutability = "MUTABLE"
}

resource "aws_lambda_function" "cognive_lambda" {
  function_name = "cognive-lambda"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda_repo.repository_url}:latest"
  
  timeout     = 30
  memory_size = 512

  environment {
    variables = {
      SECRETS_MANAGER_SECRET_NAME = data.aws_secretsmanager_secret.app_secrets.name
    }
  }
}

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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_secrets" {
  name = "lambda-secrets-policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [data.aws_secretsmanager_secret.app_secrets.arn]
    }]
  })
}