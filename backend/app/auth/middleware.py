from typing import Dict
from fastapi import HTTPException, Request, status
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from app.config.settings import settings

_clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)

def verify_clerk_token(request: Request) -> Dict[str, str]:
    try:
        print("[Auth] Starting authentication...")
        print(f"[Auth] Headers: {dict(request.headers)}")
        
        # Use authenticate_request - the official Clerk method
        request_state = _clerk_client.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=["http://localhost:3000"]  # Add your frontend URL
            )
        )
        
        print(f"[Auth] Is signed in: {request_state.is_signed_in}")
        
        if not request_state.is_signed_in:
            print(f"[Auth] Not signed in. Reason: {request_state.reason}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        payload = request_state.payload
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain user ID"
            )
        
        # Get user details
        user = _clerk_client.users.get(user_id=user_id)
        email = user.email_addresses[0].email_address if user.email_addresses else ""
        name = user.first_name or user.username or ""
        
        print(f"[Auth] Success! User: {email}")
        
        return {
            "clerk_user_id": user_id,
            "email": email,
            "name": name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Auth] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )