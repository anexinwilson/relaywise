from typing import Dict
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request, status
from app.config.settings import settings


jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)


def verify_clerk_token(request: Request) -> Dict[str, str]:
    try:
        authorization = request.headers.get("Authorization", "")
        
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing Authorization header"
            )
        
        token = authorization.split("Bearer ")[1].strip()
        
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_iat": True}
        )
        
        user_id = decoded.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain user ID"
            )
        
        email = decoded.get("email", "")
        name = decoded.get("name", "") or decoded.get("first_name", "") or decoded.get("given_name", "")
        
        if not email:
            from clerk_backend_api import Clerk
            clerk = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
            user = clerk.users.get(user_id=user_id)
            
            if user.email_addresses:
                email = user.email_addresses[0].email_address
            
            if not name:
                name = user.first_name or user.username or ""
        
        return {
            "clerk_user_id": user_id,
            "email": email,
            "name": name
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )