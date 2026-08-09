variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "deployment_phase" {
  type        = string
  description = "Bootstrap creates shared infrastructure; complete also creates the two image-based Lambda functions."
  default     = "bootstrap"

  validation {
    condition     = contains(["bootstrap", "complete"], var.deployment_phase)
    error_message = "deployment_phase must be either bootstrap or complete."
  }
}

variable "lambda_image_uri" {
  type        = string
  description = "Digest-pinned ECR image URI for the Cognive API Lambda."
  default     = null
  nullable    = true
}

variable "worker_image_uri" {
  type        = string
  description = "Digest-pinned ECR image URI for the SQS LangGraph worker Lambda."
  default     = null
  nullable    = true
}

variable "authorizer_image_uri" {
  type        = string
  description = "Digest-pinned ECR image URI for the Cognive authorizer Lambda."
  default     = null
  nullable    = true
}
