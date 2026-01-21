# AppSync GraphQL API
resource "aws_appsync_graphql_api" "main" {
  name                = "cognive-appsync"
  authentication_type = "API_KEY"
  
  schema = <<EOF
type Query {
  hello: String
  tasks: [Task]
  composioApps: AppsListResponse
}

type Mutation {
  executeComposioTask(message: String!): TaskExecutionResult
  executeMcpTask(message: String!, conversationId: String): TaskExecutionResult
}

type Task {
  id: ID!
  name: String!
  createdAt: AWSDateTime!
}

type TaskExecutionResult {
  success: Boolean!
  response: String
  conversationId: ID!
  functionCalls: [FunctionCall!]!
  error: String
}

type FunctionCall {
  name: String!
  args: AWSJSON
  result: String
}

type AppsListResponse {
  success: Boolean!
  apps: [AWSJSON!]!
  error: String
}
EOF

  log_config {
    cloudwatch_logs_role_arn = aws_iam_role.appsync_logs_role.arn
    field_log_level          = "ALL"
  }
}

# API Key for AppSync authentication
resource "aws_appsync_api_key" "main" {
  api_id      = aws_appsync_graphql_api.main.id
  description = "API key for Cognive AppSync GraphQL API"
  expires     = timeadd(timestamp(), "${var.api_key_expiration_days * 24}h")
}

# NONE data source for UNIT resolvers (direct response, no backend)
resource "aws_appsync_datasource" "none" {
  api_id = aws_appsync_graphql_api.main.id
  name   = "NONE"
  type   = "NONE"
}

# Mock resolver for hello query - UNIT resolver
resource "aws_appsync_resolver" "hello" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Query"
  field       = "hello"
  data_source = aws_appsync_datasource.none.name
  kind        = "UNIT"

  request_template = <<EOF
{
  "version": "2017-02-28",
  "payload": "Hello from AppSync!"
}
EOF

  response_template = <<EOF
$util.toJson($context.result)
EOF
}