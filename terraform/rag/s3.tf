resource "aws_s3_bucket" "composio_tools" {
  bucket = "cognive-composio-tools"
}

# Block all public access 
resource "aws_s3_bucket_public_access_block" "composio_tools" {
  bucket = aws_s3_bucket.composio_tools.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "composio_tools" {
  bucket = aws_s3_bucket.composio_tools.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}