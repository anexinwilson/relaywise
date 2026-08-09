from aws_lambda_powertools import Logger, Metrics

logger = Logger(service="cognive-api")
metrics = Metrics(namespace="Cognive", service="api")
