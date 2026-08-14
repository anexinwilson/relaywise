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

from agent.service import KEEP_RECENT_MESSAGES, MAX_HISTORY_TOKENS


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
        keep=("messages", KEEP_RECENT_MESSAGES),
        token_counter=count_tokens_approximately,
    )

    assert middleware is not None


def test_mapping_config_is_rejected() -> None:
    """Pins the mistake that broke production: these are tuples, not dicts."""
    with pytest.raises(ValueError):
        SummarizationMiddleware(
            model=FakeModel(),
            trigger={"tokens": MAX_HISTORY_TOKENS},
            keep={"messages": KEEP_RECENT_MESSAGES},
            token_counter=count_tokens_approximately,
        )


def test_history_budget_leaves_room_for_a_reply() -> None:
    """Trigger must sit well inside the model's window, not at its edge."""
    assert 0 < MAX_HISTORY_TOKENS <= 32_000
    assert KEEP_RECENT_MESSAGES > 0
