# IAM Role for Knowledge Base
resource "aws_iam_role" "bedrock_kb_role" {
  name = "bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
    }]
  })
}

# Policy for Knowledge Base to access S3
resource "aws_iam_role_policy" "bedrock_kb_s3_policy" {
  name = "bedrock-kb-s3-policy"
  role = aws_iam_role.bedrock_kb_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.composio_tools.arn,
        "${aws_s3_bucket.composio_tools.arn}/*"
      ]
    }]
  })
}

# Policy for Knowledge Base to access Secrets Manager
resource "aws_iam_role_policy" "bedrock_kb_secrets_policy" {
  name = "bedrock-kb-secrets-policy"
  role = aws_iam_role.bedrock_kb_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.pinecone_api_key.arn,
        aws_secretsmanager_secret.pinecone_connection_string.arn
      ]
    }]
  })
}

# Policy for Knowledge Base to invoke Bedrock embedding models
resource "aws_iam_role_policy" "bedrock_kb_model_policy" {
  name = "bedrock-kb-model-policy"
  role = aws_iam_role.bedrock_kb_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel"
      ]
      Resource = [
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }]
  })
}