"""Monthly credit allowance.

A spend guardrail on the LLM budget, not billing. Balances live in Redis under
a month-scoped key so the allowance resets without a scheduler — see period.py.
"""

from .credit_calculator import CreditCalculator, extract_token_counts
from .credit_checker import CreditChecker
from .period import (
    KEY_TTL_SECONDS,
    STARTING_CREDITS,
    balance_key,
    current_period,
    next_reset,
    next_reset_label,
)
from .pricing import ALLOWANCE_USD, CREDIT_VALUE_USD, usd_for_tokens

__all__ = [
    "CreditChecker",
    "CreditCalculator",
    "extract_token_counts",
    "balance_key",
    "current_period",
    "next_reset",
    "next_reset_label",
    "STARTING_CREDITS",
    "KEY_TTL_SECONDS",
    "ALLOWANCE_USD",
    "CREDIT_VALUE_USD",
    "usd_for_tokens",
]
