"""Eval cases.

Kept as plain data so they can be read, reviewed, and extended without running
anything. Each case is an input plus what a correct system should do with it.
"""

from __future__ import annotations

# --- Intent routing ----------------------------------------------------------
# The router decides whether a message can be answered conversationally or needs
# the full tool-discovery path. A false negative wastes a Composio session and
# several seconds; a false positive means a real request gets a chatty non-answer.
# This is a pure function, so it is exactly checkable.

INTENT_CASES: list[tuple[str, str | None]] = [
    # Greetings — cheap path, no tools
    ("hi", "greeting"),
    ("hello", "greeting"),
    ("hey there", None),
    ("good morning", "greeting"),
    ("hi, I'm Sam", "greeting"),
    # Who are you
    ("who are you", "identity"),
    ("what are you", "identity"),
    ("what's your name", "identity"),
    ("are you an AI", "identity"),
    # Who am I
    ("who am I", "user_identity"),
    ("what do you know about me", "user_identity"),
    ("what's my name", "user_identity"),
    ("tell me about myself", "user_identity"),
    # Capabilities
    ("what can you do", "capabilities"),
    ("how do you work", "capabilities"),
    ("what apps do you support", "capabilities"),
    # Real work — must NOT be short-circuited
    ("send a summary of today's tickets to Slack", None),
    ("what did the team say about the launch yesterday", None),
    ("check my notion", None),
    ("create a task in Linear for the login bug", None),
    ("who is on call this week", None),
    ("hi, can you check my email", None),
    ("what can you find in my Drive about pricing", None),
    ("tell me about my calendar tomorrow", None),
]

# --- Memory extraction -------------------------------------------------------
# `expected` is a list of substrings that must appear somewhere in the extracted
# content. An empty list means nothing durable should be stored — the important
# negative case, since over-eager memory poisons every later conversation.

MEMORY_CASES: list[dict] = [
    {
        "message": "I'm a freelance product designer based in Lisbon.",
        "expected": ["designer", "Lisbon"],
        "kinds": {"fact"},
    },
    {
        "message": "Always summarise in bullet points, I hate long paragraphs.",
        "expected": ["bullet"],
        "kinds": {"preference"},
    },
    {
        "message": "I work at a fintech startup and we use Notion for everything.",
        "expected": ["Notion"],
        "kinds": {"fact"},
    },
    {
        "message": "My timezone is IST, please keep that in mind for scheduling.",
        "expected": ["IST"],
        "kinds": {"fact", "preference"},
    },
    # Negatives — transient requests, nothing to remember
    {"message": "send that to the team channel", "expected": [], "kinds": set()},
    {"message": "what did Sarah say about the launch?", "expected": [], "kinds": set()},
    {"message": "create a task for the login bug", "expected": [], "kinds": set()},
    {"message": "thanks, that's perfect", "expected": [], "kinds": set()},
    # Must never store a secret
    {"message": "my api key is sk-test-12345, use it", "expected": [], "kinds": set()},
]
