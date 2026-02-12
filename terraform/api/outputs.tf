output "lambda_function_arn" {
  value = aws_lambda_function.cognive_lambda.arn
}

output "cognive_lambda_url" {
  value = aws_lambda_function_url.cognive_lambda_url.function_url
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda_repo.repository_url
}