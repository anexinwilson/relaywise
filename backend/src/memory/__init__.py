"""Conversation metadata and cross-session user memory.

Two distinct jobs:

- `ChatMemory` — conversation titles and message history, the user-visible list
- `UserMemoryStore` — durable facts carried *between* conversations

Within-conversation state is neither of these: LangGraph's Postgres
checkpointer owns it, keyed on the session id.
"""

from .chat_memory import ChatMemory
from .extraction import extract_memories
from .user_memory import UserMemoryStore, build_memory_block

__all__ = ["ChatMemory", "UserMemoryStore", "build_memory_block", "extract_memories"]
