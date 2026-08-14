"""Response shapes returned to AppSync.

These mirror the GraphQL types declared in `terraform/orchestration/appsync.tf`.
Keeping them as Pydantic models means a field rename in the schema fails loudly
here instead of silently returning null to the browser.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    """AppSync fields are camelCase; serialise with `by_alias=False` since the
    attribute names already match the GraphQL contract."""

    model_config = ConfigDict(populate_by_name=True)

    def to_appsync(self) -> dict:
        return self.model_dump(mode="json")


class ConversationSummary(CamelModel):
    sessionId: str
    chatName: str | None
    lastModifiedAt: str


class MessageView(CamelModel):
    id: str
    sender: str
    content: str
    timestamp: str
    type: str


class AgentResponse(CamelModel):
    success: bool
    response: str | None = None
    error: str | None = None
    taskId: str | None = None
    sessionId: str | None = None
    chatName: str | None = None


class DeleteResponse(CamelModel):
    success: bool
    error: str | None = None
    deletedCount: int | None = None


class UserResponse(CamelModel):
    userId: str | None
    email: str | None = None
    name: str | None = None
    tier: str = "free"
    apiCallCount: int = 0
