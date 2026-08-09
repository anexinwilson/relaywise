variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "bootstrap_mode" {
  type        = bool
  description = "When true, create shared AppSync resources without task submission resolvers."
  default     = true
}

variable "lambda_function_arn" {
  type        = string
  description = "ARN of the deployed Cognive API Lambda."
}

variable "authorizer_function_arn" {
  type        = string
  description = "ARN of the deployed Cognive Clerk authorizer Lambda."
}

variable "appsync_api_key_expires" {
  type        = string
  description = "RFC3339 expiration timestamp for the browser-visible AppSync subscription API key."
  default     = "2027-07-31T00:00:00Z"
}
