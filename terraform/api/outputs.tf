output "lambda_function_arn" {
  value = aws_lambda_function.cognive_lambda.arn
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda_repo.repository_url
}