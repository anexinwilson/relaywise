"""Resolver for `Mutation.getOrCreateUser`.

There is no user table. Clerk owns identity, and the authorizer already put the
verified claims into the resolver context, so this echoes them back in the shape
the schema declares.
"""

from __future__ import annotations

from app.graphql.context import AppSyncRequest
from app.schemas import UserResponse


def get_or_create_user(request: AppSyncRequest) -> dict:
    return UserResponse(
        userId=request.user_id,
        email=request.identity.get("email"),
        name=request.identity.get("name"),
    ).to_appsync()
