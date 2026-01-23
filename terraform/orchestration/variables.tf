variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function to grant AppSync permission to invoke"
  default     = "cognive-lambda"
}