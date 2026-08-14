resource "aws_iam_role" "appsync_logs_role" {
  name = "appsync-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "appsync.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "appsync_logs" {
  name = "appsync-logs-policy"
  role = aws_iam_role.appsync_logs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${var.aws_region}:*:*"
    }]
  })
}

resource "aws_iam_role" "appsync_lambda_role" {
  name = "appsync-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "appsync.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "appsync_lambda_policy" {
  name = "appsync-lambda-policy"
  role = aws_iam_role.appsync_lambda_role.id

  # AppSync needs BOTH sides of the permission to invoke a data source:
  # this identity-based policy on its service role, and a resource-based
  # aws_lambda_permission on the function. Adding only the second gives a 403
  # at request time with an "identity-based policy allows" message.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["lambda:InvokeFunction"]
      Resource = compact([
        var.lambda_function_arn,
        var.integrations_function_arn,
      ])
    }]
  })
}

resource "aws_iam_role_policy" "appsync_authorizer_invoke" {
  name = "appsync-authorizer-invoke-policy"
  role = aws_iam_role.appsync_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = [var.authorizer_function_arn]
    }]
  })
}
