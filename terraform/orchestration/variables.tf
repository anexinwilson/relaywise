variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function to grant AppSync permission to invoke"
  default     = "cognive-lambda"
}

variable "agentcore_endpoint" {
  type        = string
  description = "AgentCore endpoint (ngrok URL or deployed URL)"
}

variable "enable_appsync_events" {
  description = "Enable AppSync Events API for real-time agent updates"
  type        = bool
  default     = true
}