resource "aws_appsync_graphql_api" "main" {
  name                = "cognive-appsync"
  authentication_type = "AWS_LAMBDA"
  lambda_authorizer_config {
    authorizer_uri                   = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:cognive-authorizer"
    authorizer_result_ttl_in_seconds = 300
  }
  additional_authentication_provider {
    authentication_type = "API_KEY"
  }
  schema = <<EOF
type Query {
  hello: String
  askAgent(message: String!, sessionId: String): AgentResponse
    @aws_lambda
  getUserConversations: [Conversation]
  getConversationMessages(sessionId: String!): [Message]
}

type Mutation {
  getOrCreateUser: UserResponse
  publishTaskComplete(input: TaskCompleteInput!): TaskComplete
    @aws_api_key
  deleteConversation(sessionId: String!): DeleteResponse
  broadcastAgentEvent(taskId: String!, category: String!, message: String!): AgentEvent
    @aws_api_key
}

type DeleteResponse {
  success: Boolean!
  error: String
  deletedCount: Int
}

type Subscription {
  onTaskComplete(taskId: String): TaskComplete
    @aws_subscribe(mutations: ["publishTaskComplete"])
    @aws_api_key
  onAgentEvent(taskId: String): AgentEvent
    @aws_subscribe(mutations: ["broadcastAgentEvent"])
    @aws_api_key
}

type AgentResponse @aws_lambda {
  success: Boolean
  response: String
  rag_tools_found: Int
  rag_tool_names: [String]
  error: String
  taskId: String
  sessionId: String
  chatName: String
}

type TaskComplete @aws_lambda @aws_api_key {
  taskId: String!
  userId: String!
  status: String!
  result: AWSJSON
  error: String
  executionTime: Int
  timestamp: AWSDateTime!
}

type AgentEvent @aws_api_key {
  taskId: String!
  category: String!
  message: String!
  timestamp: AWSDateTime!
}

input TaskCompleteInput {
  taskId: String!
  userId: String!
  status: String!
  result: AWSJSON
  error: String
  executionTime: Int
}

type UserResponse {
  userId: String
  email: String
  name: String
  tier: String
  apiCallCount: Int
}

type Conversation {
  sessionId: String!
  chatName: String
  lastModifiedAt: String
}

type Message {
  id: String!
  sender: String!
  content: String!
  timestamp: String!
  type: String!
}
EOF
  log_config {
    cloudwatch_logs_role_arn = aws_iam_role.appsync_logs_role.arn
    field_log_level          = "ALL"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_appsync_api_key" "main" {
  api_id  = aws_appsync_graphql_api.main.id
  expires = "2027-01-31T00:00:00Z"
}

resource "aws_appsync_datasource" "lambda" {
  api_id           = aws_appsync_graphql_api.main.id
  name             = "LambdaDataSource"
  type             = "AWS_LAMBDA"
  service_role_arn = aws_iam_role.appsync_lambda_role.arn
  lambda_config {
    function_arn = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:cognive-lambda"
  }
}

resource "aws_appsync_datasource" "agentcore_http" {
  api_id           = aws_appsync_graphql_api.main.id
  name             = "AgentCoreHTTPDataSource"
  type             = "HTTP"
  service_role_arn = aws_iam_role.appsync_lambda_role.arn
  http_config {
    endpoint = var.agentcore_endpoint
  }
}

# CRITICAL: NONE datasource required for subscriptions to receive data
resource "aws_appsync_datasource" "local" {
  api_id = aws_appsync_graphql_api.main.id
  name   = "LocalDataSource"
  type   = "NONE"
}

resource "aws_lambda_permission" "appsync_invoke" {
  statement_id  = "AllowAppSyncInvoke"
  action        = "lambda:InvokeFunction"
  function_name = "cognive-lambda"
  principal     = "appsync.amazonaws.com"
}

resource "aws_lambda_permission" "appsync_authorizer_invoke" {
  statement_id  = "AllowAppSyncAuthorizerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = "cognive-authorizer"
  principal     = "appsync.amazonaws.com"
}

resource "aws_appsync_resolver" "ask_agent" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Query"
  field       = "askAgent"
  data_source = aws_appsync_datasource.agentcore_http.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<-EOF
export function request(ctx) {
  const payload = {
    action: 'ask_agent',
    userId: ctx.identity.resolverContext.userId,
    sessionId: ctx.args.sessionId || null,
    message: ctx.args.message
  };
  return {
    method: 'POST',
    resourcePath: '/invocations',
    params: {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }
  };
}
export function response(ctx) {
  const { statusCode, body } = ctx.result;
  if (statusCode === 200) {
    return JSON.parse(body);
  }
  util.appendError(body, statusCode);
  return null;
}
EOF
}

# CRITICAL: NONE resolver required for EventBridge mutations to trigger subscriptions
resource "aws_appsync_resolver" "publish_task_complete" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Mutation"
  field       = "publishTaskComplete"
  data_source = aws_appsync_datasource.local.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<-EOF
export function request(ctx) {
  return {
    payload: {
      taskId: ctx.args.input.taskId,
      userId: ctx.args.input.userId,
      status: ctx.args.input.status,
      result: ctx.args.input.result,
      error: ctx.args.input.error,
      executionTime: ctx.args.input.executionTime,
      timestamp: util.time.nowISO8601()
    }
  };
}
export function response(ctx) {
  return ctx.result;
}
EOF
}

resource "aws_appsync_resolver" "broadcast_agent_event" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Mutation"
  field       = "broadcastAgentEvent"
  data_source = aws_appsync_datasource.local.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<-EOF
export function request(ctx) {
  return {
    payload: {
      taskId: ctx.args.taskId,
      category: ctx.args.category,
      message: ctx.args.message,
      timestamp: util.time.nowISO8601()
    }
  };
}
export function response(ctx) {
  return ctx.result;
}
EOF
}

resource "aws_appsync_resolver" "get_or_create_user" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Mutation"
  field       = "getOrCreateUser"
  data_source = aws_appsync_datasource.lambda.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<EOF
export function request(ctx) {
  return {
    operation: 'Invoke',
    payload: {
      info: {
        fieldName: ctx.info.fieldName
      },
      arguments: ctx.arguments,
      request: {
        headers: ctx.identity.resolverContext
      }
    }
  };
}
export function response(ctx) {
  if (ctx.error) {
    return ctx.error;
  }
  return ctx.result;
}
EOF
}

resource "aws_appsync_resolver" "get_user_conversations" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Query"
  field       = "getUserConversations"
  data_source = aws_appsync_datasource.lambda.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<EOF
export function request(ctx) {
  return {
    operation: 'Invoke',
    payload: {
      info: {
        fieldName: ctx.info.fieldName
      },
      arguments: ctx.arguments,
      request: {
        headers: ctx.identity.resolverContext
      }
    }
  };
}
export function response(ctx) {
  if (ctx.error) {
    return ctx.error;
  }
  return ctx.result;
}
EOF
}

resource "aws_appsync_resolver" "delete_conversation" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Mutation"
  field       = "deleteConversation"
  data_source = aws_appsync_datasource.lambda.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<EOF
export function request(ctx) {
  return {
    operation: 'Invoke',
    payload: {
      info: {
        fieldName: ctx.info.fieldName
      },
      arguments: ctx.arguments,
      request: {
        headers: ctx.identity.resolverContext
      }
    }
  };
}
export function response(ctx) {
  if (ctx.error) {
    return ctx.error;
  }
  return ctx.result;
}
EOF
}

resource "aws_appsync_resolver" "get_conversation_messages" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Query"
  field       = "getConversationMessages"
  data_source = aws_appsync_datasource.lambda.name
  runtime {
    name            = "APPSYNC_JS"
    runtime_version = "1.0.0"
  }
  code = <<EOF
export function request(ctx) {
  return {
    operation: 'Invoke',
    payload: {
      info: {
        fieldName: ctx.info.fieldName
      },
      arguments: ctx.arguments,
      request: {
        headers: ctx.identity.resolverContext
      }
    }
  };
}
export function response(ctx) {
  if (ctx.error) {
    return ctx.error;
  }
  return ctx.result;
}
EOF
}
