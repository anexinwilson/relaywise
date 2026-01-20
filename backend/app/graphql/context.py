from typing import Optional
from fastapi import Request
from strawberry.fastapi import BaseContext
from composio import Composio


class GraphQLContext(BaseContext):
    def __init__(self):
        self.request: Optional[Request] = None
        self.composio_client: Optional[Composio] = None


async def get_context(request: Request) -> GraphQLContext:
    from app.app import get_composio
    
    context = GraphQLContext()
    context.request = request
    context.composio_client = get_composio()
    return context