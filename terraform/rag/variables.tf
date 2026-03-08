variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "pinecone_api_key" {
  description = "Pinecone API key used by Bedrock Knowledge Base"
  type        = string
  sensitive   = true
}

variable "pinecone_connection_string" {
  description = "Pinecone connection string / index host URL for Bedrock Knowledge Base"
  type        = string
  sensitive   = true
}