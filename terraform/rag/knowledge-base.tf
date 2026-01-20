# Reference existing Pinecone secrets
data "aws_secretsmanager_secret" "pinecone_api_key" {
  name = "bedrock-pinecone-key"
}

data "aws_secretsmanager_secret_version" "pinecone_connection_string" {
  secret_id = "pinecone-connection-string"
}

# Bedrock Knowledge Base (using Pinecone)
resource "aws_bedrockagent_knowledge_base" "composio_tools" {
  name     = "composio-tools-kb"
  role_arn = aws_iam_role.bedrock_kb_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }

  storage_configuration {
    type = "PINECONE"
    pinecone_configuration {
      connection_string      = jsondecode(data.aws_secretsmanager_secret_version.pinecone_connection_string.secret_string)["pinecone-connection-string"]
      credentials_secret_arn = data.aws_secretsmanager_secret.pinecone_api_key.arn
      namespace              = ""
      field_mapping {
        metadata_field = "metadata"
        text_field     = "text"
      }
    }
  }
}

# Data Source (S3) - syncs all .md files organized by toolkit
resource "aws_bedrockagent_data_source" "composio_tools_s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.composio_tools.id
  name              = "composio-tools-s3"
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.composio_tools.arn
      # Omit inclusion_prefixes = syncs all files in bucket
    }
  }

  # NO CHUNKING - Keep each tool intact (one file = one tool)
  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "NONE"
    }
  }
}