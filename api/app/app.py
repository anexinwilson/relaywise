from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import Base, engine, get_db, User
from app.config.redis import redis_client
from app.resolvers import user as user_resolver
from app.resolvers import conversation as conversation_resolver
from app.config.settings import settings
from svix.webhooks import Webhook
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    payload = await request.body()
    headers = request.headers
    
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")
    
    if not all([svix_id, svix_timestamp, svix_signature]):
        raise HTTPException(status_code=400, detail="Missing svix headers")
    
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, {"svix-id": svix_id, "svix-timestamp": svix_timestamp, "svix-signature": svix_signature})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    if event.get("type") == "user.created":
        data = event["data"]
        async for db in get_db():
            user = User(
                clerk_user_id=data["id"],
                email=data["email_addresses"][0]["email_address"] if data.get("email_addresses") else "",
                name=data.get("first_name") or data.get("username") or ""
            )
            db.add(user)
            await db.commit()
    
    return {"success": True}


@app.post("/webhooks/composio")
async def composio_webhook(request: Request):
    """Handle Composio account lifecycle events (e.g. connection expired)."""
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
        if field_name == "getOrCreateUser":
            import asyncio
            async def get_user():
                async for db in get_db():
                    result = await user_resolver.get_or_create_user(user_id, db)
                    return result
            return asyncio.run(get_user())
        elif field_name == "getUserConversations":
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