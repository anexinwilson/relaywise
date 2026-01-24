resource "aws_appsync_graphql_api" "main" {
  name                = "cognive-appsync"
  authentication_type = "AWS_LAMBDA"
  
  lambda_authorizer_config {
    authorizer_uri                   = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:cognive-authorizer"
    authorizer_result_ttl_in_seconds = 300
  }
  
  schema = <<EOF
type Query {
  hello: String
}

type Mutation {
  getOrCreateUser: UserResponse
}

type UserResponse {
  userId: String
  email: String
  name: String
  tier: String
  apiCallCount: Int
}
EOF

  log_config {
    cloudwatch_logs_role_arn = aws_iam_role.appsync_logs_role.arn
    field_log_level          = "ALL"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_appsync_datasource" "lambda" {
  api_id           = aws_appsync_graphql_api.main.id
  name             = "LambdaDataSource"
  type             = "AWS_LAMBDA"
  service_role_arn = aws_iam_role.appsync_lambda_role.arn
  lambda_config {
    function_arn = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:cognive-lambda"
  }
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