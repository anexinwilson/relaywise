"""What a credit is worth, in money.

Credits exist so a monthly allowance can be expressed as a budget rather than a
request count — a chatty turn and a heavy tool run should not cost the same.
The only rule that matters is the one below:

    the monthly allowance is worth ALLOWANCE_USD of model spend

Everything else is derived. Change the model, change `INPUT_USD_PER_1M` and
`OUTPUT_USD_PER_1M`, and the allowance keeps its value automatically — no
recalibrating magic numbers by hand.
"""

from __future__ import annotations

from .period import STARTING_CREDITS

# What a full monthly allowance is allowed to cost.
ALLOWANCE_USD = 0.10

# One credit's worth of spend. 100 credits -> $0.10.
CREDIT_VALUE_USD = ALLOWANCE_USD / STARTING_CREDITS

# Per-million-token price for BEDROCK_MODEL_ID, measured from the bill rather
# than a published rate card.
#
# These read 0.15/0.60 until they were checked — qwen3-32b's prices, left
# behind when the model moved to minimax-m2.5. MiniMax bills exactly double,
# so the allowance was quietly worth twice its stated value. The warning to
# check them was already here; only the checking was missing.
#
# Re-derive after any model change (Mantle does not publish rates through the
# API, and promotional credits zero out UnblendedCost, so filter to usage
# records or every figure reads $0.00):
#
#   aws ce get-cost-and-usage --granularity MONTHLY \
#     --metrics UnblendedCost UsageQuantity \
#     --group-by Type=DIMENSION,Key=USAGE_TYPE \
#     --time-period Start=<30d-ago>,End=<tomorrow> \
#     --filter '{"And":[{"Dimensions":{"Key":"SERVICE","Values":["Amazon Bedrock"]}},
#                       {"Dimensions":{"Key":"RECORD_TYPE","Values":["Usage"]}}]}'
#
# UsageQuantity is in units of 1K tokens, so:  usd_per_1m = cost / qty * 1000
INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 1.20


def credits_per_1m(usd_per_1m: float) -> float:
    """Convert a dollar price into credits."""
    return usd_per_1m / CREDIT_VALUE_USD


def usd_for_tokens(input_tokens: int, output_tokens: int) -> float:
    """Actual dollar cost of a call, for reporting and evals."""
    return (
        input_tokens / 1_000_000 * INPUT_USD_PER_1M
        + output_tokens / 1_000_000 * OUTPUT_USD_PER_1M
    )
