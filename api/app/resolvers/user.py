from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config.database import User
from app.auth.service import get_user_from_clerk


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
    
    return {
        "userId": user.clerk_user_id,
        "email": user.email,
        "name": user.name,
        "tier": user.tier,
        "apiCallCount": user.api_call_count
    }