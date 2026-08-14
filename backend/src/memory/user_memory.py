"""Cross-session memory: what the agent knows about a user between chats.

Backed by LangGraph's `AsyncPostgresStore`, the framework's own cross-thread
memory primitive. The checkpointer resumes state *within* one conversation;
the store carries durable facts *across* conversations. Together they replace
the four AgentCore memory strategies (episodic and summary from the
checkpointer, semantic and preference from here).

Records live under the namespace ("memories", user_id), so a lookup is scoped
to one user by construction rather than by remembering to add a WHERE clause.

Keys are a hash of the content, which is what gives us deduplication: stating
the same fact in a later chat writes the same key instead of a second row.
"""

from __future__ import annotations

import hashlib
from typing import Any

from langgraph.store.postgres import AsyncPostgresStore

from config import settings
from utils import get_logger

logger = get_logger(__name__)

# Caps what memory costs in prompt tokens. Older entries stay in the store but
# fall out of the injected block.
MAX_RECALLED = 40
MAX_CONTENT_CHARS = 300

NAMESPACE_PREFIX = "memories"

# DDL is idempotent but not free; run it once per warm container.
_schema_ready = False


def _namespace(user_id: str) -> tuple[str, str]:
    return (NAMESPACE_PREFIX, user_id)


def _key(content: str) -> str:
    """Stable key for a fact, so re-stating it overwrites rather than duplicates."""
    normalised = " ".join(content.lower().split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:32]


class UserMemoryStore:
    """Thin wrapper over the LangGraph store.

    Each call opens its own connection, matching how the checkpointer is used
    in `agent.service`. Lambda invocations are short and serial, so pooling
    across calls would buy little and complicate lifetime management.
    """

    async def recall(self, user_id: str) -> list[dict[str, Any]]:
        """Durable facts for a user, most recently updated first."""
        async with AsyncPostgresStore.from_conn_string(settings.DATABASE_URL) as store:
            await self._ensure_schema(store)
            items = await store.asearch(_namespace(user_id), limit=MAX_RECALLED)

        return [dict(item.value) for item in items]

    async def remember(
        self,
        user_id: str,
        entries: list[tuple[str, str]],
        session_id: str | None = None,
    ) -> int:
        """Store facts. Re-stating a known fact is a no-op by key."""
        cleaned = [
            (kind if kind in ("fact", "preference") else "fact", content.strip()[:MAX_CONTENT_CHARS])
            for kind, content in entries
            if content and content.strip()
        ]
        if not cleaned:
            return 0

        async with AsyncPostgresStore.from_conn_string(settings.DATABASE_URL) as store:
            await self._ensure_schema(store)
            for kind, content in cleaned:
                await store.aput(
                    _namespace(user_id),
                    _key(content),
                    {"kind": kind, "content": content, "session_id": session_id},
                )

        logger.info("Stored %s memories for user %s", len(cleaned), user_id)
        return len(cleaned)

    @staticmethod
    async def _ensure_schema(store: AsyncPostgresStore) -> None:
        global _schema_ready
        if not _schema_ready:
            await store.setup()
            _schema_ready = True


def build_memory_block(memories: list[dict[str, Any]]) -> str:
    """Render recalled memories for the system prompt.

    Same [MEMORY] envelope the AgentCore context manager produced, so the
    prompt template did not need to change.
    """
    if not memories:
        return ""

    facts = [m["content"] for m in memories if m.get("kind") == "fact" and m.get("content")]
    preferences = [
        m["content"] for m in memories if m.get("kind") == "preference" and m.get("content")
    ]

    sections = []
    if facts:
        sections.append("Facts about the user:\n" + "\n".join(f"- {f}" for f in facts))
    if preferences:
        sections.append("User preferences:\n" + "\n".join(f"- {p}" for p in preferences))

    if not sections:
        return ""
    return "[MEMORY]\n" + "\n\n".join(sections) + "\n[/MEMORY]\n"
