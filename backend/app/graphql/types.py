import strawberry


@strawberry.type
class User:
    clerk_user_id: str
    email: str
    name: str 