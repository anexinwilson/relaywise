import io
"""Guard the agent's middleware configuration.

`SummarizationMiddleware` validates its arguments in `__init__`, which happens
inside `ExecutionAgent.execute` — so a bad config is not caught until a real
task runs, and it takes the whole tool-execution path down while the
personality path keeps working. That is a nasty failure to notice by hand, so
construct it here instead.
"""

import pytest
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages.utils import count_tokens_approximately

from agent.service import KEEP_RECENT_TOKENS, MAX_HISTORY_TOKENS


class FakeModel:
    """Minimal stand-in.

    The middleware inspects `_llm_type` to pick a token counter, so the stub
    has to expose it even though no call is ever made.
    """

    _llm_type = "openai-chat"


def test_summarization_config_is_valid() -> None:
    middleware = SummarizationMiddleware(
        model=FakeModel(),
        trigger=("tokens", MAX_HISTORY_TOKENS),
        keep=("tokens", KEEP_RECENT_TOKENS),
        token_counter=count_tokens_approximately,
    )

    assert middleware is not None


def test_mapping_config_is_rejected() -> None:
    """Pins the mistake that broke production: these are tuples, not dicts."""
    with pytest.raises(ValueError):
        SummarizationMiddleware(
            model=FakeModel(),
            trigger={"tokens": MAX_HISTORY_TOKENS},
            keep={"tokens": KEEP_RECENT_TOKENS},
            token_counter=count_tokens_approximately,
        )


def test_history_budget_leaves_room_for_a_reply() -> None:
    """Trigger must sit well inside the model's window, not at its edge."""
    assert 0 < MAX_HISTORY_TOKENS <= 32_000
    assert KEEP_RECENT_TOKENS > 0


def test_kept_history_is_measured_in_tokens() -> None:
    """`keep` must be a token budget, not a message count.

    The default is ("messages", 20). A single tool message can carry an entire
    API response, so twenty of them is an unbounded number of tokens: replayed
    history grew from 27k to 267k tokens across one conversation before this
    was changed.
    """
    from agent import service

    source = (service.__file__ or "").replace(".pyc", ".py")
    text = io.open(source, encoding="utf-8").read() if source else ""

    assert 'keep=("tokens"' in text
    assert 'keep=("messages"' not in text


def test_kept_history_is_smaller_than_the_trigger() -> None:
    """Summarising must actually shrink the thread."""
    assert KEEP_RECENT_TOKENS < MAX_HISTORY_TOKENS
