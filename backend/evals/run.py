"""Run the eval suite.

    uv run python -m evals.run              # everything
    uv run python -m evals.run intent       # deterministic only, no API calls

Two kinds of check live here, and the distinction matters:

- **Intent routing** is a pure function. It is exactly checkable, costs nothing,
  and belongs in CI on every commit.
- **Memory extraction** calls the model, so it costs money and is not perfectly
  repeatable. Run it when the prompt changes, not on every push.

Set LANGSMITH_TRACING=true in backend/.env.local to see traces. The suite works
without LangSmith — it just prints to the terminal instead. The key belongs on
your machine and in CI, never in AWS: this never runs in Lambda.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv(".env.local")

from agent.intent import detect_personality_intent  # noqa: E402
from evals.datasets import INTENT_CASES, MEMORY_CASES  # noqa: E402


@dataclass
class Report:
    name: str
    passed: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def record(self, ok: bool, detail: str) -> None:
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(detail)

    @property
    def total(self) -> int:
        return self.passed + self.failed

    def render(self) -> str:
        rate = (self.passed / self.total * 100) if self.total else 0.0
        lines = [f"\n{self.name}: {self.passed}/{self.total} ({rate:.0f}%)"]
        lines += [f"  FAIL  {f}" for f in self.failures]
        lines += [f"  note  {n}" for n in self.notes]
        return "\n".join(lines)


def eval_intent_routing() -> Report:
    """Exact-match over a pure function. No model, no cost, safe for CI."""
    report = Report("Intent routing")
    for message, expected in INTENT_CASES:
        actual = detect_personality_intent(message)
        report.record(
            actual == expected,
            f"{message!r}: expected {expected}, got {actual}",
        )
    return report


async def eval_memory_extraction() -> Report:
    """Does extraction capture durable facts and, crucially, ignore everything else?"""
    from langchain_openai import ChatOpenAI

    from config import settings
    from memory.extraction import extract_memories

    report = Report("Memory extraction")
    llm = ChatOpenAI(
        api_key=settings.BEDROCK_MANTLE_API_KEY,
        base_url=settings.BEDROCK_MANTLE_BASE_URL,
        model=settings.BEDROCK_MODEL_ID,
        temperature=0,
        max_tokens=512,
    )

    for case in MEMORY_CASES:
        entries = await extract_memories(llm, case["message"])
        blob = " ".join(content for _, content in entries).lower()

        if not case["expected"]:
            # Negative case: storing anything here is the failure.
            report.record(
                not entries,
                f"{case['message']!r}: expected nothing stored, got {entries}",
            )
            continue

        missing = [term for term in case["expected"] if term.lower() not in blob]
        report.record(
            not missing,
            f"{case['message']!r}: missing {missing} in {entries}",
        )

        kinds = {kind for kind, _ in entries}
        if case["kinds"] and kinds and not (kinds & case["kinds"]):
            report.notes.append(
                f"{case['message']!r}: classified {kinds}, expected one of {case['kinds']}"
            )

    return report


async def eval_token_cost() -> Report:
    """Where do the tokens actually go?

    Not pass/fail — a measurement. Production shows ~3,500 input tokens for a
    one-line request against ~11 output, so cost is dominated by what we *send*,
    not what the model writes. This isolates the two things we control: the
    memory block and the extraction call.
    """
    from langchain_core.messages.utils import count_tokens_approximately
    from langchain_openai import ChatOpenAI

    from config import settings
    from memory.extraction import EXTRACTION_PROMPT, extract_memories
    from memory.user_memory import MAX_RECALLED, build_memory_block

    report = Report("Token cost")

    prompt_tokens = count_tokens_approximately(
        [{"role": "system", "content": EXTRACTION_PROMPT}]
    )
    report.notes.append(f"extraction system prompt: ~{prompt_tokens} tokens per message")

    # A full memory block at the recall cap, to bound what memory can ever add.
    worst_case = [
        {"kind": "fact", "content": "The user is a freelance product designer based in Lisbon."}
        for _ in range(MAX_RECALLED)
    ]
    block_tokens = count_tokens_approximately(
        [{"role": "system", "content": build_memory_block(worst_case)}]
    )
    report.notes.append(
        f"memory block at the {MAX_RECALLED}-entry cap: ~{block_tokens} tokens per request"
    )
    report.record(
        block_tokens < 2000,
        f"memory block is {block_tokens} tokens at cap, which is a large share of every prompt",
    )

    llm = ChatOpenAI(
        api_key=settings.BEDROCK_MANTLE_API_KEY,
        base_url=settings.BEDROCK_MANTLE_BASE_URL,
        model=settings.BEDROCK_MODEL_ID,
        temperature=0,
        max_tokens=512,
    )
    skipped = await extract_memories(llm, "ok")
    report.record(
        skipped == [],
        "short messages should skip the extraction call entirely, not pay for it",
    )
    report.notes.append("short messages skip extraction, saving one model call per turn")

    return report


async def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    reports = [eval_intent_routing()]

    if which in ("all", "memory"):
        reports.append(await eval_memory_extraction())
    if which in ("all", "tokens"):
        reports.append(await eval_token_cost())
    if which == "intent":
        pass
    elif which not in ("all", "memory", "tokens"):
        print(f"unknown suite {which!r}; use: intent | memory | tokens | all")
        return 2

    if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
        print(f"Tracing to LangSmith project {os.getenv('LANGSMITH_PROJECT', 'default')!r}")

    for report in reports:
        print(report.render())

    failed = sum(r.failed for r in reports)
    print(f"\n{'FAILED' if failed else 'PASSED'} — {failed} failing case(s)\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
