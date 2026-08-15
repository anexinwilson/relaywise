# Alerting and cost guardrails.
#
# These exist because of a real outage: a laptop-local COMPOSIO_CACHE_DIR
# reached the worker's configuration, Composio raised at import, and every
# invocation died before the handler loaded. It went unnoticed until someone
# used the app and got silence back.
#
# The lesson shapes what is alarmed here. Powertools emitted TaskFailed 3 times
# while 9 requests actually failed, because a crash during module import
# happens before Powertools is imported and can report anything. So both alarms
# below watch metrics AWS emits on our behalf — Lambda Errors and queue depth —
# which survive the process dying. Custom metrics are for insight, not for
# alerting on whether the service is alive.

resource "aws_sns_topic" "alerts" {
  name = "relaywise-alerts"
}

# Email needs a click to confirm; until then the subscription sits "pending"
# and alarms fire into nothing. Check your inbox after the first apply.
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Anything here has already failed three times and been given up on, so a
# single message is worth waking up for. This is also the only signal that
# catches a task lost to a crash the code never got to observe.
resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name        = "relaywise-dlq-not-empty"
  alarm_description = "A task exhausted its retries and was dead-lettered."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  dimensions  = { QueueName = aws_sqs_queue.agent_tasks_dlq.name }

  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# Two consecutive five-minute windows with errors, rather than a threshold on
# one window. The outage produced exactly 2 errors per window, so a "3 or more"
# rule would have watched it happen in silence; requiring two windows in a row
# still ignores a single transient failure.
resource "aws_cloudwatch_metric_alarm" "worker_errors" {
  count = var.deployment_phase == "complete" ? 1 : 0

  alarm_name        = "relaywise-worker-errors"
  alarm_description = "The agent worker is failing invocations repeatedly."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions  = { FunctionName = aws_lambda_function.agent_worker[0].function_name }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# A ceiling on model spend.
#
# Read this honestly: a budget NOTIFIES, it cannot STOP. AWS has no mechanism
# to halt Bedrock at a dollar figure. The thing that actually limits spend is
# the per-user credit allowance in Redis, which refuses work before the call is
# made. This budget is the backstop that tells you the allowance is not holding
# — a bug, an unexpected price change, or abuse.
#
# Thresholds are deliberately early: 50% arrives while there is still time to
# act, and FORECASTED catches a spike on the day it starts rather than at
# month end.
resource "aws_budgets_budget" "bedrock" {
  name         = "relaywise-bedrock-monthly"
  budget_type  = "COST"
  limit_amount = var.bedrock_monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "Service"
    values = ["Amazon Bedrock"]
  }

  # Promotional credits currently zero out the bill. Excluding them means this
  # tracks what the usage is genuinely worth, so the alarm still works while
  # the credits last and does not suddenly start firing when they run out.
  cost_types {
    include_credit = false
    include_refund = false
  }

  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

# Keeping the free-tier data stores awake.
#
# Neon and Upstash reclaim idle resources, and a portfolio project is idle by
# nature: the person most likely to open it is a stranger doing so months after
# it was last touched. A suspended database greets them with a connection
# error, which is worse than no demo at all.
#
# Every three days is well inside any provider's inactivity window while adding
# roughly ten invocations a month, which is free. The target is the existing
# API function, so this costs no extra image, no extra IAM role and nothing to
# keep patched.
resource "aws_cloudwatch_event_rule" "keepalive" {
  count = var.deployment_phase == "complete" ? 1 : 0

  name                = "relaywise-keepalive"
  description         = "Reads from Postgres and Redis so neither is reclaimed for inactivity."
  schedule_expression = "rate(3 days)"
}

resource "aws_cloudwatch_event_target" "keepalive" {
  count = var.deployment_phase == "complete" ? 1 : 0

  rule = aws_cloudwatch_event_rule.keepalive[0].name
  arn  = aws_lambda_function.api[0].arn

  # detail-type is what handler.py matches on to tell this apart from an
  # AppSync resolver payload or an HTTP proxy event.
  input = jsonencode({ "detail-type" = "relaywise.keepalive" })
}

resource "aws_lambda_permission" "keepalive" {
  count = var.deployment_phase == "complete" ? 1 : 0

  statement_id  = "AllowKeepaliveInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.keepalive[0].arn
}

# A store unreachable for two consecutive runs means roughly six days of
# failure, which is long enough to be a real outage and not a blip.
resource "aws_cloudwatch_metric_alarm" "keepalive_failing" {
  count = var.deployment_phase == "complete" ? 1 : 0

  alarm_name        = "relaywise-keepalive-failing"
  alarm_description = "Postgres or Redis has been unreachable across repeated keepalive runs."

  namespace   = "Relaywise"
  metric_name = "KeepaliveFailed"
  dimensions  = { service = "api" }

  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}
