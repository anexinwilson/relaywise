"""Decide what is worth remembering about a user between conversations.

Runs on the user's message alone, not the whole transcript. That keeps the call
cheap — a few hundred input tokens — and avoids the model "remembering" its own
replies back at itself, which is how memory systems drift into nonsense.

Extraction is best effort. Anything unparseable is dropped rather than guessed
at: a wrong memory is worse than a missing one, because it persists and
contaminates every later conversation.
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from utils import get_logger

logger = get_logger(__name__)

MAX_ENTRIES = 5

EXTRACTION_PROMPT = """You extract durable facts about a user from their message.

Return a JSON array. Each element is an object with:
  "kind": "fact" for stable information about the user, "preference" for how
          they like things done
  "content": one short self-contained sentence, written in the third person

Record ONLY things that stay true beyond this conversation:
- who they are, where they are, what they work on, what tools they use
- standing preferences about how they want things done

Do NOT record:
- one-off requests, questions, or commands
- anything about the current task
- passwords, tokens, card numbers, or other secrets
- guesses; if the message states no durable fact, return []

Examples:
"send that to the team channel" -> []
"I'm a freelance designer based in Lisbon" ->
  [{"kind":"fact","content":"The user is a freelance designer based in Lisbon."}]
"always summarise in bullet points, I hate long paragraphs" ->
  [{"kind":"preference","content":"The user prefers bullet-point summaries over long paragraphs."}]

Return only the JSON array, nothing else."""


def _parse(raw: str) -> list[tuple[str, str]]:
    """Pull a JSON array out of the reply, tolerating code fences."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()

    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        logger.debug("Memory extraction returned unparseable JSON")
        return []

    if not isinstance(parsed, list):
        return []

    entries: list[tuple[str, str]] = []
    for item in parsed[:MAX_ENTRIES]:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        kind = str(item.get("kind", "fact")).strip().lower()
        entries.append((kind if kind in ("fact", "preference") else "fact", content))
    return entries


async def extract_memories(llm, user_message: str) -> list[tuple[str, str]]:
    """Durable facts stated in this message, or an empty list."""
    if not user_message or len(user_message.strip()) < 12:
        # Too short to carry a durable fact; skip the call entirely.
        return []

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=EXTRACTION_PROMPT),
                HumanMessage(content=user_message),
            ]
        )
    except Exception as exc:
        logger.warning("Memory extraction call failed: %s", exc)
        return []

    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )

    return _parse(str(content))
