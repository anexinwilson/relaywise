from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import Base, engine, get_db, User
from app.config.redis import redis_client
from app.resolvers import user as user_resolver
from app.resolvers import conversation as conversation_resolver
from app.config.settings import settings
from app.auth.service import get_current_user
from svix.webhooks import Webhook
import json
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
        user_id = data["id"]
        
        async for db in get_db():
            user = User(
                clerk_user_id=user_id,
                email=data["email_addresses"][0]["email_address"] if data.get("email_addresses") else "",
                name=data.get("first_name") or data.get("username") or ""
            )
            db.add(user)
            await db.commit()
        
        # Initialize user credits with 30-day TTL
        try:
            credit_key = f"user_credits:{user_id}"
            # SET with NX flag ensures we don't overwrite existing credits
            # EX sets TTL to 2592000 seconds (30 days)
            result = redis_client.set(credit_key, "100.0", nx=True, ex=2592000)
            if result:
                logger.info(
                    f"Initialized credits for user {user_id}: 100.0 credits with 30-day TTL",
                    extra={
                        "user_id": user_id,
                        "operation": "credit_initialization",
                        "credits": 100.0,
                        "ttl_seconds": 2592000
                    }
                )
            else:
                logger.info(
                    f"Credits already exist for user {user_id}, skipping initialization",
                    extra={"user_id": user_id, "operation": "credit_initialization"}
                )
        except Exception as e:
            # Fail-open: log error at ERROR level but continue user creation
            logger.error(
                f"Redis error initializing credits for user {user_id}: {e}",
                extra={
                    "user_id": user_id,
                    "operation": "credit_initialization",
                    "error": str(e)
                },
                exc_info=True
            )
            # Log fallback at WARNING level
            logger.warning(
                f"User {user_id} created without credit initialization due to Redis error",
                extra={"user_id": user_id, "operation": "credit_initialization"}
            )
    
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


@app.get("/api/credits/balance")
async def get_credits_balance(current_user: User = Depends(get_current_user)):
    """Fetch current credit balance for authenticated user"""
    user_id = current_user.clerk_user_id
    
    try:
        key = f"user_credits:{user_id}"
        remaining = redis_client.get(key)
        
        if remaining is None:
            # Key doesn't exist - credits not initialized or expired
            logger.warning(
                f"No credit key found for user {user_id}",
                extra={"user_id": user_id, "operation": "get_credits_balance"}
            )
            return {
                "remaining_credits": 0.0,
                "total_credits": 100.0,
                "used_credits": 100.0
            }
        
        # Convert bytes to float if necessary
        if isinstance(remaining, bytes):
            remaining = remaining.decode("utf-8")
        
        remaining_float = float(remaining)
        used = max(0.0, 100.0 - remaining_float)
        
        # Log successful credit fetch at INFO level
        logger.info(
            f"Fetched credits for user {user_id}: {remaining_float} remaining",
            extra={
                "user_id": user_id,
                "operation": "get_credits_balance",
                "remaining_credits": remaining_float
            }
        )
        
        return {
            "remaining_credits": remaining_float,
            "total_credits": 100.0,
            "used_credits": used
        }
        
    except Exception as e:
        # Log Redis error at ERROR level with full context
        logger.error(
            f"Redis error fetching credits for user {user_id}: {e}",
            extra={
                "user_id": user_id,
                "operation": "get_credits_balance",
                "error": str(e)
            },
            exc_info=True
        )
        # Log fallback at WARNING level
        logger.warning(
            f"Falling back to default credits (100.0) for user {user_id} due to Redis error",
            extra={"user_id": user_id, "operation": "get_credits_balance"}
        )
        return {
            "remaining_credits": 100.0,
            "total_credits": 100.0,
            "used_credits": 0.0,
            "error": "Failed to fetch credits from Redis"
        }


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