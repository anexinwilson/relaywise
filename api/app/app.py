from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config.redis import redis_client
from app.resolvers import conversation as conversation_resolver
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhooks/composio")
async def composio_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type")
    data = payload.get("data", {})

    if event_type == "composio.connected_account.expired":
        account_id = data.get("id")
        slug = data.get("toolkit", {}).get("slug")

        if account_id and slug:
            owner_key = f"account_owner:{account_id}"
            user_id = redis_client.get(owner_key)

            if user_id:
                if isinstance(user_id, bytes):
                    user_id = user_id.decode("utf-8")
                redis_client.hdel(f"connected_apps:{user_id}", slug)
                redis_client.delete(owner_key)
                print(f"Composio webhook: cleaned up expired {slug} for user {user_id}")

    return {"success": True}


def graphql_resolver(event: dict):
    field_name = event.get("info", {}).get("fieldName")
    user_id = event.get("request", {}).get("headers", {}).get("userId")
    
    try:
        if field_name == "getUserConversations":
            if not user_id:
                return []
            result = conversation_resolver.get_user_conversations(None, None, user_id)
            if isinstance(result, dict) and 'conversations' in result:
                return result['conversations']
            return result
        elif field_name == "getConversationMessages":
            if not user_id:
                return []
            arguments = event.get("arguments", {})
            session_id = arguments.get("sessionId")
            if not session_id:
                return []
            result = conversation_resolver.get_conversation_messages(None, None, user_id, session_id)
            return result
        elif field_name == "deleteConversation":
            if not user_id:
                return {"success": False, "error": "Unauthorized"}
            arguments = event.get("arguments", {})
            session_id = arguments.get("sessionId")
            if not session_id:
                return {"success": False, "error": "sessionId is required"}
            result = conversation_resolver.delete_conversation(None, None, user_id, session_id)
            return result
        else:
            return []
    except Exception as e:
        print(f"Error in graphql_resolver: {e}")
        if field_name in ["getUserConversations", "getConversationMessages"]:
            return []
        return {"error": str(e), "success": False}
