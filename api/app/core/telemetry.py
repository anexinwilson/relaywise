"""Powertools logger and metrics for the API Lambda.

Every module logs through this logger so that keys appended by the entrypoint
(field_name, user_id, session_id) appear on records emitted deeper in the call
stack, and one CloudWatch filter returns a whole request.
"""

from aws_lambda_powertools import Logger, Metrics

SERVICE_NAME = "relaywise-api"
METRICS_NAMESPACE = "Relaywise"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(namespace=METRICS_NAMESPACE, service="api")
