import strawberry
from datetime import datetime
from strawberry.scalars import JSON

@strawberry.type
class User:
    clerk_user_id: str
    email: str
    name: str 

@strawberry.type
class Task:
    id: str
    name: str
    created_at: datetime


@strawberry.type
class AppInfo:
    name: str
    key: str

@strawberry.type
class AppsListResponse:
    success: bool
    apps: list[JSON]
    error: str | None