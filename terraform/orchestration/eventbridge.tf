resource "aws_cloudwatch_event_bus" "agentcore" {
  name = "cognive-agentcore-events"
}

resource "aws_cloudwatch_event_connection" "appsync_connection" {
  name               = "cognive-appsync-connection"
  description        = "Connection to AppSync GraphQL API"
  authorization_type = "API_KEY"
  auth_parameters {
    api_key {
      key   = "x-api-key"
      value = aws_appsync_api_key.main.key
    }
  }
}

resource "aws_cloudwatch_event_api_destination" "appsync_destination" {
  name                             = "cognive-appsync-destination"
  description                      = "AppSync GraphQL API destination"
  invocation_endpoint              = aws_appsync_graphql_api.main.uris["GRAPHQL"]
  http_method                      = "POST"
  invocation_rate_limit_per_second = 100
  connection_arn                   = aws_cloudwatch_event_connection.appsync_connection.arn
}

resource "aws_cloudwatch_event_rule" "task_complete" {
  name           = "cognive-task-complete"
  description    = "Route AgentCore task completion events to AppSync"
  event_bus_name = aws_cloudwatch_event_bus.agentcore.name
  event_pattern = jsonencode({
    source      = ["agentcore.tasks"]
    detail-type = ["Task Complete"]
  })
}

resource "aws_cloudwatch_event_target" "appsync_target" {
  rule           = aws_cloudwatch_event_rule.task_complete.name
  event_bus_name = aws_cloudwatch_event_bus.agentcore.name
  target_id      = "AppSyncAPIDestination"
  arn            = aws_cloudwatch_event_api_destination.appsync_destination.arn
  role_arn       = aws_iam_role.eventbridge_invoke_api_destination.arn
  http_target {
    header_parameters = {
      "Content-Type" = "application/json"
    }
  }
  input_transformer {
    input_paths = {
      taskId        = "$.detail.taskId"
      userId        = "$.detail.userId"
      status        = "$.detail.status"
      result        = "$.detail.result"
      error         = "$.detail.error"
      executionTime = "$.detail.executionTime"
    }
    input_template = <<-EOT
{
  "query": "mutation PublishTaskComplete($input: TaskCompleteInput!) { publishTaskComplete(input: $input) { taskId userId status result error executionTime timestamp } }",
  "variables": {
    "input": {
      "taskId": "<taskId>",
      "userId": "<userId>",
      "status": "<status>",
      "result": <result>,
      "error": "<error>",
      "executionTime": <executionTime>
    }
  }
}
EOT
  }
}

resource "aws_iam_role" "eventbridge_invoke_api_destination" {
  name = "cognive-eventbridge-invoke-api-destination"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_invoke_api_destination" {
  name = "cognive-eventbridge-invoke-api-destination-policy"
  role = aws_iam_role.eventbridge_invoke_api_destination.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["events:InvokeApiDestination"]
      Resource = aws_cloudwatch_event_api_destination.appsync_destination.arn
    }]
  })
}
