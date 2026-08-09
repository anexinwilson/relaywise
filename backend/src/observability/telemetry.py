from aws_lambda_powertools import Logger, Metrics

logger = Logger(service="relaywise-agent")
metrics = Metrics(namespace="Relaywise", service="agent-worker")
