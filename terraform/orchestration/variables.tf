variable "aws_region" {
  description = "AWS region for AppSync resources"
  type        = string
  default     = "us-east-1"
}

variable "api_key_expiration_days" {
  description = "Number of days until API key expires (AWS limit: 1-365 days)"
  type        = number
  default     = 365
}