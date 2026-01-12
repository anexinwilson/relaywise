from typing import Optional
from strawberry.fastapi import BaseContext
from fastapi import Request

class GraphQLContext(BaseContext):
    def __init__(self):
        self.request: Optional[Request] = None

async def get_context(request: Request) -> GraphQLContext:
    context = GraphQLContext()
    context.request = request
    return context