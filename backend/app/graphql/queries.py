import strawberry
from app.graphql.types import User, Task, AppsListResponse, AppInfo
from app.graphql.context import GraphQLContext
from app.auth.middleware import verify_clerk_token
from app.config.database import AsyncSessionLocal
from sqlalchemy import select
from app.config.database import Task as TaskModel
from app.integrations.service import get_integration_service


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

    @strawberry.field
    async def composio_apps(
        self, 
        info: strawberry.Info[GraphQLContext, None]
    ) -> AppsListResponse:
        try:
            genai_client = info.context.request.app.state.genai_client
            service = get_integration_service(genai_client)
            result = await service.list_available_apps()
            
            return AppsListResponse(
                success=result["success"],
                apps=result["apps"],
                error=result.get("error")
            )
        except Exception as e:
            return AppsListResponse(
                success=False,
                apps=[],
                error=str(e)
            )