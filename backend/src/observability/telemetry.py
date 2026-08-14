from aws_lambda_powertools import Logger, Metrics

# Every logger in the worker image hangs off this name so that keys appended by
# the Lambda entrypoint (task_id, session_id, user_id) reach records emitted
# deep inside the agent. See utils.get_logger.
SERVICE_NAME = "relaywise-agent"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(namespace="Relaywise", service="agent-worker")
