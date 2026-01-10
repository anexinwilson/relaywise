import strawberry
from sqlalchemy import select
from app.auth.middleware import verify_clerk_token
from app.config.database import AsyncSessionLocal, Project as ProjectModel
from app.graphql.types import Project
from app.graphql.context import GraphQLContext


@strawberry.type
class ProjectMutations:
    @strawberry.mutation
    async def create_project(self, name: str, info: strawberry.Info[GraphQLContext, None]) -> Project:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            project = ProjectModel(user_id=user_info["clerk_user_id"], name=name)
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            return Project(id=project.id, name=project.name, created_at=project.created_at)
    
    @strawberry.mutation
    async def update_project(self, project_id: str, name: str, info: strawberry.Info[GraphQLContext, None]) -> Project:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProjectModel).where(
                    ProjectModel.id == project_id,
                    ProjectModel.user_id == user_info["clerk_user_id"]
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise Exception("Project not found")
            
            project.name = name
            await db.commit()
            await db.refresh(project)
            
            return Project(id=project.id, name=project.name, created_at=project.created_at)
    
    @strawberry.mutation
    async def delete_project(self, project_id: str, info: strawberry.Info[GraphQLContext, None]) -> bool:
        user_info = verify_clerk_token(info.context.request)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProjectModel).where(
                    ProjectModel.id == project_id,
                    ProjectModel.user_id == user_info["clerk_user_id"]
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise Exception("Project not found")
            
            await db.delete(project)
            await db.commit()
            
            return True