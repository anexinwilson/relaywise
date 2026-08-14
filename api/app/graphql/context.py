"""Normalised view of an AppSync Lambda invocation.

AppSync resolvers in this project are written in APPSYNC_JS and each builds its
own payload, so the identity arrives in one of two shapes depending on the
resolver. Parsing that in one place keeps every resolver free of the difference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UnauthorizedError(Exception):
    """Raised when a field requiring a signed-in user has no trusted identity."""


@dataclass(frozen=True)
class AppSyncRequest:
    field_name: str
    arguments: dict[str, Any]
    identity: dict[str, Any]

    @property
    def user_id(self) -> str | None:
        """Clerk subject, as established by the Lambda authorizer.

        This is never taken from client-supplied arguments — the authorizer is
        the only trusted source.
        """
        return self.identity.get("userId")

    def require_user_id(self) -> str:
        user_id = self.user_id
        if not user_id:
            raise UnauthorizedError("Authenticated user required")
        return user_id

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> AppSyncRequest:
        payload = event.get("payload", event)
        identity = (payload.get("identity") or {}).get("resolverContext") or {}
        if not identity:
            # Resolvers that forward `ctx.identity.resolverContext` as
            # `request.headers` rather than as `identity`.
            identity = (payload.get("request") or {}).get("headers") or {}

        return cls(
            field_name=(payload.get("info") or {}).get("fieldName", ""),
            arguments=payload.get("arguments") or {},
            identity=identity,
        )
