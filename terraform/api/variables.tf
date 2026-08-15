variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "deployment_phase" {
  type        = string
  description = <<-EOT
    "bootstrap" creates only shared infrastructure (ECR, queues, secret, IAM) so
    images can be pushed before any function exists. "complete" also creates the
    three image-based Lambdas and the SQS event source mapping.

    Defaults to "complete" deliberately: a bare `terraform apply` must not tear
    down running functions just because someone forgot a -var flag.
  EOT
  default     = "complete"

  validation {
    condition     = contains(["bootstrap", "complete"], var.deployment_phase)
    error_message = "deployment_phase must be either bootstrap or complete."
  }
}

variable "lambda_image_uri" {
  type        = string
  description = "Digest-pinned ECR image URI for the API Lambda."
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
  description = "Digest-pinned ECR image URI for the Clerk authorizer Lambda."
  default     = null
  nullable    = true
}

variable "worker_max_concurrency" {
  type        = number
  description = <<-EOT
    Ceiling on concurrent agent tasks across all users. This is a cap, not a
    reservation — raising it costs nothing when idle, and prevents one user's
    task from making everyone else wait. AWS requires a minimum of 2.
  EOT
  default     = 10

  validation {
    condition     = var.worker_max_concurrency >= 2 && var.worker_max_concurrency <= 1000
    error_message = "worker_max_concurrency must be between 2 and 1000."
  }
}

variable "alert_email" {
  type        = string
  description = <<-EOT
    Address that receives alarm and budget notifications.

    Deliberately has no default: this repository is public, and a personal
    address committed to it is a spam target. Set it in terraform.tfvars,
    which is git-ignored.
  EOT

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}

variable "bedrock_monthly_budget_usd" {
  type        = string
  description = <<-EOT
    Monthly ceiling on Bedrock spend, in dollars.

    A budget notifies; it cannot stop spending. The real limit is the per-user
    credit allowance in Redis, which refuses work before a call is made. This
    is the backstop for when that allowance is not doing its job.
  EOT
  default     = "5"
}

variable "cors_allowed_origins" {
  type        = string
  description = <<-EOT
    Comma-separated origins allowed to call the HTTP surface.

    Both the deployed frontend and local development are listed, so neither
    needs changing when the other is worked on.
  EOT
  default     = "http://localhost:3000,https://relaywise-seven.vercel.app"
}
