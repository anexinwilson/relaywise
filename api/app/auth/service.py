from typing import Dict
from fastapi import HTTPException, status, Request, Depends
from clerk_backend_api import Clerk
from app.config.settings import settings
from app.config.database import User, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

_clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)


def verify_clerk_token(request: Request) -> Dict[str, str]:
    """Verify Clerk token from request headers"""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Verify the token with Clerk
        verified = _clerk_client.jwt_templates.verify_token(token)
        user_id = verified.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return {"clerk_user_id": user_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Get current authenticated user from database"""
    user_info = verify_clerk_token(request)
    user_id = user_info["clerk_user_id"]
    
    stmt = select(User).where(User.clerk_user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def get_user_from_clerk(user_id: str) -> Dict[str, str]:
    """Fetch user data from Clerk API"""
    try:
        user = _clerk_client.users.get(user_id=user_id)
        return {
            "clerk_user_id": user_id,
            "email": user.email_addresses[0].email_address if user.email_addresses else "",
            "name": user.first_name or user.username or ""
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user from Clerk: {str(e)}"
        )