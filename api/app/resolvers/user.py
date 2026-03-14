import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config.database import User
from app.auth.service import get_user_from_clerk
from app.config.redis import redis_client

logger = logging.getLogger(__name__)


async def get_or_create_user(user_id: str, db: AsyncSession) -> dict:
    user_data = await get_user_from_clerk(user_id)
    
    stmt = select(User).where(User.clerk_user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        user.email = user_data.get("email", user.email)
        user.name = user_data.get("name", user.name)
    else:
        user = User(
            clerk_user_id=user_id,
            email=user_data.get("email"),
            name=user_data.get("name"),
            tier="free"
        )
        db.add(user)
    
    await db.commit()
    await db.refresh(user)
    
    # Credit re-initialization logic: check if Redis key exists
    try:
        key = f"user_credits:{user_id}"
        balance = redis_client.get(key)
        
        if balance is None:
            # Key missing (expired or never initialized) - re-initialize with 100.0 credits and 30-day TTL
            # Use NX flag to prevent overwriting if key was just created by another request
            result = redis_client.set(key, 100.0, nx=True, ex=2592000)
            if result:
                logger.info(
                    f"Re-initialized credits for user {user_id}: 100.0 credits with 30-day TTL",
                    extra={
                        "user_id": user_id,
                        "operation": "credit_reinitialization",
                        "credits": 100.0,
                        "ttl_seconds": 2592000
                    }
                )
            else:
                logger.info(
                    f"Credits already initialized for user {user_id} by concurrent request",
                    extra={"user_id": user_id, "operation": "credit_reinitialization"}
                )
    except Exception as e:
        # Fail-open: log error at ERROR level and continue without blocking login
        logger.error(
            f"Redis error during credit check/re-initialization for user {user_id}: {e}",
            extra={
                "user_id": user_id,
                "operation": "credit_reinitialization",
                "error": str(e)
            },
            exc_info=True
        )
        # Log fallback at WARNING level
        logger.warning(
            f"User {user_id} login proceeding without credit check due to Redis error",
            extra={"user_id": user_id, "operation": "credit_reinitialization"}
        )
    
    return {
        "userId": user.clerk_user_id,
        "email": user.email,
        "name": user.name,
        "tier": user.tier,
        "apiCallCount": user.api_call_count
    }