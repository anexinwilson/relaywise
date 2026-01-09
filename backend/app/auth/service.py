from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import User


async def get_or_create_user(
    clerk_user_id: str,
    email: str,
    name: str | None,
    db: AsyncSession
) -> User:
    """Get user by clerk_user_id or create if doesn't exist."""
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        if email and user.email != email:
            user.email = email
        if name and user.name != name:
            user.name = name
        await db.commit()
        await db.refresh(user)
        return user
    
    user = User(clerk_user_id=clerk_user_id, email=email, name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user