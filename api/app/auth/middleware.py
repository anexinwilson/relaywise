from fastapi import Request, HTTPException, status
from app.auth.service import verify_clerk_token


async def auth_middleware(request: Request, call_next):
    if request.url.path in ["/health", "/graphql-resolver"]:
        return await call_next(request)
    
    try:
        user_info = verify_clerk_token(request)
        request.state.user = user_info
        return await call_next(request)
    except HTTPException as e:
        raise e