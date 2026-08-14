variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "bootstrap_mode" {
  type        = bool
  description = <<-EOT
    When true, creates the AppSync API without the askAgent resolver, so the
    API can exist before the Lambda that serves it.

    Defaults to false deliberately: a bare `terraform apply` must not delete a
    working resolver just because someone forgot a -var flag.
  EOT
  default     = false
}

variable "lambda_function_arn" {
  type        = string
  description = "ARN of the deployed Relaywise API Lambda (terraform/api output api_function_arn)."
}

variable "authorizer_function_arn" {
  type        = string
  description = "ARN of the deployed Clerk authorizer Lambda (terraform/api output authorizer_function_arn)."
}

variable "appsync_api_key_expires" {
  type        = string
  description = <<-EOT
    RFC3339 expiry for the browser-visible subscription API key.

    Browser subscriptions stop working on this date with no alarm. Tracked in
    scratch/audits as item F1: the long-term fix is moving subscriptions behind
    the Clerk authorizer so the browser needs no key at all.
  EOT
  default     = "2027-07-31T00:00:00Z"
}

variable "integrations_function_arn" {
  type        = string
  description = <<-EOT
    ARN of the connected-app control-plane Lambda (terraform/api output
    integrations_function_arn). Null skips the integrations resolvers, so the
    stack can be applied before that function exists.
  EOT
  default     = null
  nullable    = true
}
