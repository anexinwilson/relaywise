"""Compare candidate models on this workload.

    uv run python -m evals.compare_models
    uv run python -m evals.compare_models moonshotai.kimi-k2.5 deepseek.v3.2

Mantle publishes no pricing through its API, so this measures the half we can
measure: how many tokens a model spends and whether it gets the answer right.
Multiply by the per-million price from your bill to get cost — `credits/pricing.py`
already derives credit rates that way.

Why tokens matter more than the headline rate here: a model that resolves a task
in two calls is cheaper than a nominally cheaper one that takes six, because each
call re-sends the whole tool schema. Rate is a poor proxy for spend on an agent
workload.

The instruction-following section targets the two behaviours that broke in
production: inventing a plausible default instead of using discovered data, and
stopping to ask permission before a read.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv(".env.local")

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

from config import settings  # noqa: E402
from evals.datasets import MEMORY_CASES  # noqa: E402
from memory.extraction import extract_memories  # noqa: E402

CANDIDATES = [
    "minimax.minimax-m2.5",  # current — the only one that completed the task
    "deepseek.v3.2",
    "moonshotai.kimi-k2.5",
    "qwen.qwen3-32b",
    "zai.glm-4.7-flash",
]

# Measured on a real agent run ("check my latest message in slack") against a
# live Slack workspace. The synthetic checks below could not tell these models
# apart — all five passed — which is why the choice was made on this instead:
#
#   model            tokens  credits   time  outcome
#   minimax-m2.5     18,624     1.23    37s  correct, named the exact message
#   deepseek-v3.2    45,900     2.98    58s  correct, 2.4x the cost
#   kimi-k2.5        10,956     0.68    34s  gave up and asked which channel
#   qwen3-32b        31,580     1.95    45s  wrong channel, asked permission
#
# Cheapest is not best here: a request that ends in a question costs its tokens
# and still needs a follow-up.

# Mirrors the real failure: a conventional-sounding option exists, but the data
# says otherwise. A model that answers "general" has picked the default over the
# evidence, which is exactly what went wrong with a live workspace.
DISCIPLINE_PROMPT = """You are an assistant with tool access.

A list_channels call returned exactly this:
  [{"name": "new-channel", "id": "C0A86BWC407", "message_count": 2},
   {"name": "general", "id": "C0A9G4005H6", "message_count": 0}]

The user asked: "check my latest message"

Reply with ONE line only, in this form:
ACTION: <the channel name you will read from>

Do not ask any question. Do not explain."""


@dataclass
class Result:
    model: str
    ok: bool = False
    error: str = ""
    extraction_correct: int = 0
    extraction_total: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    picks_evidence: bool = False
    asks_permission: bool = False
    notes: list[str] = field(default_factory=list)


def _client(model: str, max_tokens: int = 512) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.BEDROCK_MANTLE_API_KEY,
        base_url=settings.BEDROCK_MANTLE_BASE_URL,
        model=model,
        temperature=0,
        max_tokens=max_tokens,
    )


async def _discipline(model: str, result: Result) -> None:
    """Does it follow the evidence, and does it act without being asked twice?"""
    response = await _client(model, max_tokens=64).ainvoke(
        [SystemMessage(content=DISCIPLINE_PROMPT), HumanMessage(content="Go.")]
    )
    text = str(response.content).lower()
    usage = getattr(response, "usage_metadata", None) or {}
    result.input_tokens += usage.get("input_tokens", 0)
    result.output_tokens += usage.get("output_tokens", 0)

    result.picks_evidence = "new-channel" in text
    result.asks_permission = "?" in text or "would you like" in text
    if not result.picks_evidence:
        result.notes.append(f"chose: {text.strip()[:60]!r}")


async def _extraction(model: str, result: Result) -> None:
    """Quality on a task we already have labelled cases for."""
    llm = _client(model)
    for case in MEMORY_CASES:
        entries = await extract_memories(llm, case["message"])
        blob = " ".join(c for _, c in entries).lower()
        expected = case["expected"]
        correct = (
            not entries
            if not expected
            else all(term.lower() in blob for term in expected)
        )
        result.extraction_total += 1
        result.extraction_correct += int(correct)


async def measure(model: str) -> Result:
    result = Result(model=model)
    started = time.monotonic()
    try:
        await _discipline(model, result)
        await _extraction(model, result)
        result.ok = True
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {str(exc)[:80]}"
    result.seconds = time.monotonic() - started
    return result


def render(results: list[Result]) -> str:
    header = (
        f"{'model':<26} {'extract':>9} {'evidence':>9} {'no-ask':>7} "
        f"{'tokens':>8} {'secs':>6}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        if not r.ok:
            lines.append(f"{r.model:<26} {r.error}")
            continue
        rate = f"{r.extraction_correct}/{r.extraction_total}"
        lines.append(
            f"{r.model:<26} {rate:>9} "
            f"{'yes' if r.picks_evidence else 'NO':>9} "
            f"{'yes' if not r.asks_permission else 'NO':>7} "
            f"{r.input_tokens + r.output_tokens:>8} {r.seconds:>6.1f}"
        )
        for note in r.notes:
            lines.append(f"{'':<26} {note}")
    return "\n".join(lines)


async def main() -> int:
    models = sys.argv[1:] or CANDIDATES
    print(f"Comparing {len(models)} models on this workload.\n")

    results = []
    for model in models:
        print(f"  running {model} ...", flush=True)
        results.append(await measure(model))

    print()
    print(render(results))
    print(
        "\nextract  = labelled memory-extraction cases passed"
        "\nevidence = used the channel the data showed, not the conventional default"
        "\nno-ask   = acted instead of asking permission for a read"
        "\ntokens   = total for this comparison, not per request"
        "\n\nMultiply tokens by your per-million rate for cost; Mantle does not"
        "\npublish pricing through the API."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
