import strawberry
from sqlalchemy import select
from app.auth.middleware import verify_clerk_token
from app.config.database import AsyncSessionLocal, Task as TaskModel
from app.graphql.types import Task
from app.graphql.context import GraphQLContext


@strawberry.type
class TaskMutations:
    @strawberry.mutation
    async def create_task(self, name: str, info: strawberry.Info[GraphQLContext, None]) -> Task:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            task = TaskModel(user_id=user_info["clerk_user_id"], name=name)
            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            return Task(id=task.id, name=task.name, created_at=task.created_at)
    
    @strawberry.mutation
    async def update_task(self, task_id: str, name: str, info: strawberry.Info[GraphQLContext, None]) -> Task:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TaskModel).where(
                    TaskModel.id == task_id,
                    TaskModel.user_id == user_info["clerk_user_id"]
                )
            )
            task = result.scalar_one_or_none()
            
            if not task:
                raise Exception("Task not found")
            
            task.name = name
            await db.commit()
            await db.refresh(task)
            
            return Task(id=task.id, name=task.name, created_at=task.created_at)
    
    @strawberry.mutation
    async def delete_task(self, task_id: str, info: strawberry.Info[GraphQLContext, None]) -> bool:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TaskModel).where(
                    TaskModel.id == task_id,
                    TaskModel.user_id == user_info["clerk_user_id"]
                )
            )
            task = result.scalar_one_or_none()
            
            if not task:
                raise Exception("Task not found")
            
            await db.delete(task)
            await db.commit()
            
            return True