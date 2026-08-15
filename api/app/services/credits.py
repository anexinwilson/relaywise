"""Monthly credit allowance, read side.

Mirrors `backend/src/credits/period.py`. The two deployment units ship as
separate images and share no code, so the key format is duplicated here
deliberately — if you change it, change it in both places and in
`frontend/src/app/api/credits/balance/route.ts`.

The API only ever *checks*. Deduction happens in the worker, where real token
counts are known.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.clients import get_redis
from app.core.telemetry import logger

STARTING_CREDITS = 100.0
# 31 days, the length of the longest month. The floor is a key created in the
# first moment of a 31 day month: expiry then lands exactly on the next
# period's boundary, so a live balance is never wiped mid-month. The reset
# itself comes from the month in the key name, not from this value.
# Mirrored in backend/src/credits/period.py; change both together.
KEY_TTL_SECONDS = 31 * 24 * 60 * 60


def current_period(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


def balance_key(user_id: str, now: datetime | None = None) -> str:
    return f"user_credits:{user_id}:{current_period(now)}"


def next_reset(now: datetime | None = None) -> datetime:
    """First instant of the next period, in UTC."""
    moment = now or datetime.now(timezone.utc)
    if moment.month == 12:
        return datetime(moment.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(moment.year, moment.month + 1, 1, tzinfo=timezone.utc)


def next_reset_label(now: datetime | None = None) -> str:
    """The reset date as a reader would write it, e.g. "1 September 2026".

    Built by hand rather than strftime("%-d"), which is glibc only and raises
    on Windows where the tests run.
    """
    moment = next_reset(now)
    return f"{moment.day} {moment:%B %Y}"


def check_credits(user_id: str) -> tuple[bool, float]:
    """Whether this user may start a task, and what remains.

    A missing key means a new period, not an exhausted one — seed and allow.
    Any Redis failure denies: an outage must not authorize an unmetered run.
    """
    key = balance_key(user_id)
    try:
        redis = get_redis()
        balance = redis.get(key)

        if balance is None:
            redis.setnx(key, STARTING_CREDITS)
            redis.expire(key, KEY_TTL_SECONDS)
            logger.info("Seeded a new credit period", credits=STARTING_CREDITS)
            return True, STARTING_CREDITS

        remaining = float(balance)
        if remaining <= 0:
            logger.warning("Credits exhausted for this period", remaining=remaining)
            return False, remaining
        return True, remaining

    except Exception as exc:  # noqa: BLE001 - fail closed on purpose
        logger.exception("Credit check failed", error_type=type(exc).__name__)
        return False, 0.0
