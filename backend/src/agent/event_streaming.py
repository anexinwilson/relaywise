import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


def stream_event(task_id: str, category: str, message: str) -> bool:
    """
    Broadcasts a live execution event to the Next.js frontend via AppSync GraphQL.
    Example: stream_event(task_id, "execute", "Discovering connected-app tools")
    """
    try:
        endpoint = settings.APPSYNC_EVENTS_ENDPOINT
        api_key = settings.APPSYNC_API_KEY

        if not endpoint or not api_key:
            logger.warning("AppSync credentials missing. Cannot broadcast event.")
            return False

        # Properly escaped GraphQL mutation String
        query = """
        mutation BroadcastAgentEvent(
            $taskId: String!
            $category: String!
            $message: String!
        ) {
            broadcastAgentEvent(
                taskId: $taskId
                category: $category
                message: $message
            ) {
                taskId
                category
                message
                timestamp
            }
        }
        """

        variables = {"taskId": task_id, "category": category, "message": message}

        headers = {"Content-Type": "application/json", "x-api-key": api_key}

        payload = {"query": query, "variables": variables}

        response = httpx.post(endpoint, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        logger.info("Broadcasted event to AppSync: %s -> %s", category, message)
        return True

    except Exception as e:
        logger.error("Failed to broadcast Agent Event: %s", e)
        return False
