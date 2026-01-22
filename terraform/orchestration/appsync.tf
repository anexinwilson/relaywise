resource "aws_appsync_graphql_api" "main" {
  name                = "cognive-appsync"
  authentication_type = "API_KEY"
  
  schema = <<EOF
type Query {
  hello: String
}

type Mutation {
  testMutation(message: String!): TestResponse
}

type TestResponse {
  result: String
  success: Boolean
}
EOF

  log_config {
    cloudwatch_logs_role_arn = aws_iam_role.appsync_logs_role.arn
    field_log_level          = "ALL"
  }
}

resource "aws_appsync_api_key" "main" {
  api_id      = aws_appsync_graphql_api.main.id
  description = "API key for Cognive AppSync"
  expires     = timeadd(timestamp(), "8760h")
}

resource "aws_appsync_datasource" "lambda" {
  api_id           = aws_appsync_graphql_api.main.id
  name             = "LambdaDataSource"
  type             = "AWS_LAMBDA"
  service_role_arn = aws_iam_role.appsync_lambda_role.arn
  lambda_config {
    function_arn = local.lambda_function_arn
  }
}

resource "aws_appsync_resolver" "test_mutation" {
  api_id      = aws_appsync_graphql_api.main.id
  type        = "Mutation"
  field       = "testMutation"
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
      field: 'testMutation',
      arguments: ctx.arguments,
      request: {
        headers: ctx.request.headers
      },
      info: {
        fieldName: ctx.info.fieldName,
        parentTypeName: ctx.info.parentTypeName
      }
    }
  };
}

export function response(ctx) {
  return ctx.result;
}
EOF
}