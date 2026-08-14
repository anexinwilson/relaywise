resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "relaywise/lambda/secrets"
  description = "Runtime configuration for the Relaywise API, worker, and Clerk authorizer"

  # Deletion is a 7-day soft delete, which is the window to recover from an
  # accidental destroy.
  recovery_window_in_days = 7

  lifecycle {
    # Values are entered out-of-band and are not in state. Recreating this
    # resource silently produces an empty secret and every Lambda fails at cold
    # start, so a destroy must be an explicit, deliberate act.
    prevent_destroy = true
  }
}
