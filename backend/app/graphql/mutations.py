import strawberry
from fastapi import Request

from app.auth.middleware import verify_clerk_token
from app.auth.service import get_or_create_user
from app.config.database import AsyncSessionLocal
from app.graphql.types import User


from strawberry.fastapi import BaseContext

class GraphQLContext(BaseContext):
    def __init__(self, request: Request):
        super().__init__()
        self.request = request


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def sync_user(self, info: strawberry.Info[GraphQLContext, None]) -> User:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            user = await get_or_create_user(
                clerk_user_id=user_info["clerk_user_id"],
                email=user_info["email"],
                name=user_info["name"],
                db=db
            )
            
            return User(
                clerk_user_id=user.clerk_user_id,
                email=user.email,
                name=user.name
            )