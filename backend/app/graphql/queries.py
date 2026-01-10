import strawberry
from app.graphql.types import Project
from app.graphql.context import GraphQLContext
from app.auth.middleware import verify_clerk_token
from app.config.database import AsyncSessionLocal
from sqlalchemy import select
from app.config.database import Project as ProjectModel


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello World"

    @strawberry.field
    async def projects(self, info: strawberry.Info[GraphQLContext, None]) -> list[Project]:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProjectModel).where(ProjectModel.user_id == user_info["clerk_user_id"])
            )
            projects = result.scalars().all()
            
            return [
                Project(id=p.id, name=p.name, created_at=p.created_at)
                for p in projects
            ]