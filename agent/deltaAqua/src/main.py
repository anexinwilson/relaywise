import os
import json
import httpx
from datetime import datetime
from bedrock_agentcore import BedrockAgentCoreApp
from agent import get_agent_service
from utils import get_logger

logger = get_logger(__name__)

app = BedrockAgentCoreApp()
agent_service = get_agent_service()

EVENTS_ENDPOINT = os.getenv('APPSYNC_EVENTS_ENDPOINT', '')
EVENTS_API_KEY = os.getenv('APPSYNC_EVENTS_API_KEY', '')

async def publish_progress(session_id: str, progress: str, message: str):
    """Publish progress to AppSync events"""
    if not EVENTS_ENDPOINT or not EVENTS_API_KEY:
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f'{EVENTS_ENDPOINT}/channels/agent-{session_id}',
                json={
                    'progress': progress,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat(),
                },
                headers={
                    'x-api-key': EVENTS_API_KEY,
                    'Content-Type': 'application/json'
                },
                timeout=10.0
            )
    except Exception as e:
        logger.error(f'Events error: {e}')

@app.entrypoint
async def invoke(payload):
    """Main entry point for agent"""
    try:
        user_id = payload.get("userId")
        message = payload.get("message")
        session_id = payload.get("sessionId", "")

        if not user_id or not message:
            logger.warning("Missing userId or message in payload")
            return {"error": "Missing userId or message", "success": False}

        logger.info(f"Invoking agent - user: {user_id}, session: {session_id}")
        await publish_progress(session_id, "0%", "Starting...")

        result = await agent_service.execute_task(
            user_message=message,
            user_id=user_id,
            conversation_id=session_id
        )

        await publish_progress(session_id, "100%", "Complete")

        return {
            "success": True,
            "response": result.get("response"),
            "rag_tools_found": result.get("rag_tools_found"),
            "rag_tool_names": result.get("rag_tool_names"),
        }

    except Exception as e:
        logger.error(f"Invocation error: {e}")
        await publish_progress(session_id, "error", str(e))
        return {"error": str(e), "success": False}

if __name__ == "__main__":
    app.run()