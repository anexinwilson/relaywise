from fastapi import Request
from strawberry.fastapi import BaseContext


class GraphQLContext(BaseContext):
    def __init__(self, request: Request):
        super().__init__()
        self.request = request