from typing import Dict
from fastapi import HTTPException, status
from clerk_backend_api import Clerk
from app.config.settings import settings

_clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)


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