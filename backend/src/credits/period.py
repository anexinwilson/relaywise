"""Monthly credit periods.

The allowance resets on a calendar month boundary. Rather than run a scheduler
to zero balances, the period is encoded in the key itself:

    user_credits:{user_id}:2026-08

August's key is simply never read again once September starts, and September's
is seeded on first use. The TTL is garbage collection, not the mechanism — it
only stops abandoned keys accumulating in Redis, so its exact value is not
load-bearing.
"""

from __future__ import annotations

from datetime import datetime, timezone

STARTING_CREDITS = 100.0

# Comfortably longer than any month, so a key never expires while its period is
# still current.
KEY_TTL_SECONDS = 45 * 24 * 60 * 60


def current_period(now: datetime | None = None) -> str:
    """Calendar month in UTC, e.g. "2026-08"."""
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m")


def next_reset(now: datetime | None = None) -> datetime:
    """First instant of the next period, in UTC.

    Telling someone they are out of credits without saying when that ends
    leaves them with nothing to do but guess. Derived from the same month
    boundary the key uses, so the date shown is the date the balance
    actually returns.
    """
    moment = now or datetime.now(timezone.utc)
    if moment.month == 12:
        return datetime(moment.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(moment.year, moment.month + 1, 1, tzinfo=timezone.utc)


def next_reset_label(now: datetime | None = None) -> str:
    """The reset date as a reader would write it, e.g. "1 September 2026".

    Built by hand rather than with strftime("%-d"): that directive is glibc
    only and raises on Windows, where the tests and evals also run.
    """
    moment = next_reset(now)
    return f"{moment.day} {moment:%B %Y}"


def balance_key(user_id: str, now: datetime | None = None) -> str:
    return f"user_credits:{user_id}:{current_period(now)}"
