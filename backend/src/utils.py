import logging

from observability.telemetry import SERVICE_NAME


def get_logger(name: str) -> logging.Logger:
    """Return a module logger that emits through Powertools.

    Naming each logger `relaywise-agent.<module>` makes it a child of the
    Powertools logger, so records propagate to that handler and are rendered as
    JSON carrying whatever keys the entrypoint appended (task_id, session_id,
    user_id). Emitting through a bare StreamHandler instead — as this used to —
    produced unstructured text with no correlation, which is precisely the case
    where the agent has failed and the logs need to explain why.

    The module name is preserved in the `name` field, so a failing call site is
    still identifiable in CloudWatch.
    """
    return logging.getLogger(f"{SERVICE_NAME}.{name}")
