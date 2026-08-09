import re
from typing import Literal

PersonalityIntent = Literal[
    "greeting",
    "identity",
    "user_identity",
    "capabilities",
]


def detect_personality_intent(message: str) -> PersonalityIntent | None:
    """Route only unambiguous conversational requests without an LLM call."""
    normalized = re.sub(r"[^a-z0-9' ]+", " ", message.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)

    if re.search(
        r"\b(who am i|what(?:'s| is) my name|what do you know about me|"
        r"tell me about myself)\b",
        normalized,
    ):
        return "user_identity"

    if re.search(
        r"\b(who are you|what are you|what(?:'s| is) your name|are you an ai)\b",
        normalized,
    ):
        return "identity"

    if re.search(
        r"\b(what can you do|how do you work|what apps do you support|"
        r"what are your capabilities)\b",
        normalized,
    ):
        return "capabilities"

    greeting = re.fullmatch(
        r"(?:hi|hello|hey|good morning|good afternoon|good evening|nice to meet you)"
        r"(?:[ ,]+(?:i am|i'm|my name is) [a-z0-9' -]+)?",
        normalized,
    )
    if greeting:
        return "greeting"

    return None
