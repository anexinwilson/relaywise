import strawberry
from datetime import datetime

@strawberry.type
class User:
    clerk_user_id: str
    email: str
    name: str 

@strawberry.type
class Project:
    id: str
    name: str
    created_at: datetime