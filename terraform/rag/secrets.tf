resource "aws_secretsmanager_secret" "pinecone_api_key" {
  name = "bedrock-pinecone-key"
}

resource "aws_secretsmanager_secret_version" "pinecone_api_key" {
  secret_id = aws_secretsmanager_secret.pinecone_api_key.id
  secret_string = jsonencode({
    apiKey = var.pinecone_api_key
  })
}

resource "aws_secretsmanager_secret" "pinecone_connection_string" {
  name = "pinecone-connection-string"
}

resource "aws_secretsmanager_secret_version" "pinecone_connection_string" {
  secret_id = aws_secretsmanager_secret.pinecone_connection_string.id
  secret_string = jsonencode({
    "pinecone-connection-string" = var.pinecone_connection_string
  })
}
