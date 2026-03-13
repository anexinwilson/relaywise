import os
import json
import httpx
import asyncio
import uuid
import threading
import time
import boto3
from datetime import datetime
from bedrock_agentcore import BedrockAgentCoreApp
from agent import get_agent_service
from agent.sync import disconnect_app, handle_expired_webhook, get_auth_url, sync_connections_to_redis
from agent.client import get_redis_client
from utils import get_logger
from dotenv import load_dotenv

load_dotenv('.env.local')

logger = get_logger(__name__)

app = BedrockAgentCoreApp()
agent_service = get_agent_service()

EVENTS_ENDPOINT = os.getenv('APPSYNC_EVENTS_ENDPOINT', '')
EVENTS_API_KEY = os.getenv('APPSYNC_EVENTS_API_KEY', '')
EVENTBRIDGE_BUS_NAME = os.getenv('EVENTBRIDGE_BUS_NAME')

if not EVENTBRIDGE_BUS_NAME:
    raise ValueError("EVENTBRIDGE_BUS_NAME environment variable is required")

eventbridge = boto3.client('events', region_name='us-east-1')

task_mapping = {}

async def publish_progress(session_id: str, progress: str, message: str):
    if not EVENTS_ENDPOINT or not EVENTS_API_KEY:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f'{EVENTS_ENDPOINT}/channels/agent-{session_id}',
                json={'progress': progress, 'message': message, 'timestamp': datetime.utcnow().isoformat()},
                headers={'x-api-key': EVENTS_API_KEY, 'Content-Type': 'application/json'},
                timeout=10.0
            )
    except Exception as e:
        logger.error(f'Events error: {e}')

def publish_task_complete(task_id: str, user_id: str, status: str, result=None, error=None, execution_time=0):
    try:
        detail = {
            "taskId": task_id,
            "userId": user_id,
            "status": status,
            "result": json.dumps(result) if result is not None else None,
            "error": error if error else "",
            "executionTime": execution_time
        }
        
        detail = {k: v for k, v in detail.items() if v is not None}
        
        event_entry = {
            'Source': 'agentcore.tasks',
            'DetailType': 'Task Complete',
            'Detail': json.dumps(detail),
            'EventBusName': EVENTBRIDGE_BUS_NAME
        }
        
        logger.info(f"Publishing EventBridge event: {json.dumps(event_entry, indent=2)}")
        
        response = eventbridge.put_events(Entries=[event_entry])
        
        logger.info(f"EventBridge response: {response}")
        
        if response.get('FailedEntryCount', 0) > 0:
            logger.error(f"EventBridge publish failed: {response.get('Entries', [])}")
        else:
            logger.info(f"EventBridge event published successfully: {task_id} -> {status}")
    except Exception as e:
        logger.error(f"EventBridge publish failed: {e}", exc_info=True)

def run_agent_background(task_id: str, agentcore_task_id: str, user_id: str, message: str, session_id: str, chat_name: str = None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_time = time.time()
    try:
        logger.info(f"[BACKGROUND] Task {task_id} started")
        result = loop.run_until_complete(
            agent_service.execute_task(user_message=message, user_id=user_id, conversation_id=session_id, chat_name=chat_name)
        )
        execution_time = int((time.time() - start_time) * 1000)
        publish_task_complete(
            task_id=task_id,
            user_id=user_id,
            status="COMPLETED",
            result=result,
            execution_time=execution_time
        )
        app.complete_async_task(agentcore_task_id)
        logger.info(f"[BACKGROUND] Task {task_id} completed in {execution_time}ms")
    except Exception as e:
        logger.error(f"[BACKGROUND] Task {task_id} failed: {e}", exc_info=True)
        execution_time = int((time.time() - start_time) * 1000)
        publish_task_complete(
            task_id=task_id,
            user_id=user_id,
            status="FAILED",
            error=str(e),
            execution_time=execution_time
        )
        app.complete_async_task(agentcore_task_id)
    finally:
        loop.close()

@app.entrypoint
async def handler(payload):
    try:
        action = payload.get("action")
        logger.info(f"Handler called with action: {action}")
        if action == "ask_agent":
            return await ask_agent_handler(payload)
        elif action == "disconnect_app":
            return await disconnect_app_handler(payload)
        elif action == "webhook":
            return await webhook_handler(payload)
        elif action == "get_auth_url":
            return await get_auth_url_handler(payload)
        elif action == "sync_connections":
            return await sync_connections_handler(payload)
        else:
            return {"error": f"Unknown action: {action}", "success": False}
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        return {"error": str(e), "success": False}

async def ask_agent_handler(payload):
    try:
        user_id = payload.get("userId")
        message = payload.get("message")
        session_id = payload.get("sessionId") or str(uuid.uuid4())
        if not user_id or not message:
            return {"error": "Missing userId or message", "success": False}

        # Get or generate chat name SYNCHRONOUSLY before returning
        chat_name = None
        try:
            # Check if this is the first message in the session
            is_first = agent_service.chat_memory.is_first_message(user_id, session_id)
            
            if is_first:
                # Generate chat name from user message (only for new conversations)
                chat_name = await agent_service.chat_namer.generate_chat_name(message)
                if chat_name:
                    chat_name = chat_name.strip('"\' ').strip()
                    if chat_name:
                        # Store chat name with special metadata
                        agent_service.chat_memory.store_message(user_id, session_id, chat_name, 'ASSISTANT', is_chat_name=True)
                        logger.info(f"Stored chat name for new session: {chat_name}")
            
            # Always retrieve the persisted chat name (for both new and existing sessions)
            persisted_chat_name = agent_service.chat_memory.get_chat_name(user_id, session_id)
            if persisted_chat_name:
                chat_name = persisted_chat_name
                logger.info(f"Using persisted chat name: {chat_name}")
        except Exception as e:
            logger.error(f"Chat name generation failed: {e}")

        task_id = str(uuid.uuid4())
        agentcore_task_id = app.add_async_task(f"agent_processing_{task_id}")
        task_mapping[task_id] = agentcore_task_id

        thread = threading.Thread(
            target=run_agent_background,
            args=(task_id, agentcore_task_id, user_id, message, session_id, chat_name),
            daemon=True
        )
        thread.start()

        logger.info(f"Task {task_id} started with session {session_id}")
        return {
            "success": True,
            "taskId": task_id,
            "sessionId": session_id,
            "response": "Processing your request...",
            "rag_tools_found": 0,
            "rag_tool_names": [],
            "chatName": chat_name,
        }
    except Exception as e:
        logger.error(f"ask_agent error: {e}", exc_info=True)
        return {"error": str(e), "success": False}

async def disconnect_app_handler(payload):
    try:
        user_id = payload.get("userId")
        app_slug = payload.get("appSlug")
        connected_account_id = payload.get("connectedAccountId")

        if not user_id or not app_slug:
            return {"error": "Missing userId or appSlug", "success": False}

        success = await disconnect_app(user_id, app_slug, connected_account_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"disconnect_app error: {e}", exc_info=True)
        return {"error": str(e), "success": False}

async def webhook_handler(payload):
    try:
        event_type = payload.get("type")
        data = payload.get("data", {})
        success = handle_expired_webhook(event_type, data)
        return {"success": success}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"success": False, "error": str(e)}

async def get_auth_url_handler(payload):
    try:
        user_id = payload.get("userId")
        app_slug = payload.get("appSlug")
        if not user_id or not app_slug:
            return {"error": "Missing userId or appSlug", "success": False}
        url = await get_auth_url(user_id, app_slug)
        if url:
            return {"success": True, "url": url}
        return {"success": False, "error": "Failed to generate auth URL"}
    except Exception as e:
        logger.error(f"get_auth_url error: {e}", exc_info=True)
        return {"error": str(e), "success": False}

async def sync_connections_handler(payload):
    try:
        user_id = payload.get("userId")
        if not user_id:
            return {"error": "Missing userId", "success": False}
        await sync_connections_to_redis(user_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"sync_connections error: {e}", exc_info=True)
        return {"error": str(e), "success": False}

@app.ping
def health_check():
    from bedrock_agentcore.runtime import PingStatus
    return PingStatus.HEALTHY_BUSY

if __name__ == "__main__":
    app.run()