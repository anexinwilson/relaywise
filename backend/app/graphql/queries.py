import strawberry
from app.graphql.types import Task
from app.graphql.context import GraphQLContext
from app.auth.middleware import verify_clerk_token
from app.config.database import AsyncSessionLocal
from sqlalchemy import select
from app.config.database import Task as TaskModel


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello World"

    @strawberry.field
    async def tasks(self, info: strawberry.Info[GraphQLContext, None]) -> list[Task]:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TaskModel).where(TaskModel.user_id == user_info["clerk_user_id"])
            )
            tasks = result.scalars().all()
            
            return [
                Task(id=t.id, name=t.name, created_at=t.created_at)
                for t in tasks
            ]