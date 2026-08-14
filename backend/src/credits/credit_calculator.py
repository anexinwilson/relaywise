from aws_lambda_powertools.metrics import MetricUnit
from upstash_redis import Redis

from observability.telemetry import metrics
from utils import get_logger

from .period import KEY_TTL_SECONDS, balance_key
from .pricing import (
    INPUT_USD_PER_1M,
    OUTPUT_USD_PER_1M,
    credits_per_1m,
    usd_for_tokens,
)

logger = get_logger(__name__)


def extract_token_counts(result: dict) -> tuple[int, int]:
    """Total tokens billed for one agent run.

    A tool-using turn is a loop, not a single call: the model is invoked once to
    choose a tool, again once the tool returns, and again to write the reply.
    Each of those is a separately billed request that re-sends the whole system
    prompt and tool schemas.

    Input must therefore be summed across every call, exactly like output. Taking
    only the last message's input — as this did — ignored every earlier call and
    undercharged multi-step runs several times over, which for a spend guardrail
    means the cap does not cap anything.
    """
    messages = result.get("messages", [])
    ai_messages = [
        m for m in messages if hasattr(m, "usage_metadata") and m.usage_metadata
    ]

    if not ai_messages:
        logger.error("No usage_metadata found in any AI message")
        return 0, 0

    input_tokens = sum(m.usage_metadata.get("input_tokens", 0) for m in ai_messages)
    output_tokens = sum(m.usage_metadata.get("output_tokens", 0) for m in ai_messages)

    return input_tokens, output_tokens


class CreditCalculator:
    """Turns real token usage into credits.

    Rates are derived from the model's dollar price, not hand-tuned, so the
    monthly allowance keeps a fixed cash value across model changes. See
    pricing.py.
    """

    INPUT_COST_PER_1M = credits_per_1m(INPUT_USD_PER_1M)
    OUTPUT_COST_PER_1M = credits_per_1m(OUTPUT_USD_PER_1M)

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)

    def calculate_credits(
        self,
        input_tokens: int,
        output_tokens: int,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> float:
        input_tokens = max(0, input_tokens)
        output_tokens = max(0, output_tokens)

        credits_used = (input_tokens / 1_000_000 * self.INPUT_COST_PER_1M) + (
            output_tokens / 1_000_000 * self.OUTPUT_COST_PER_1M
        )

        usd_cost = usd_for_tokens(input_tokens, output_tokens)

        # Spend as a metric, not only a log field.
        #
        # Cost Explorer is the authority on what you are billed, but it lags
        # roughly a day — too slow to answer "is something burning money right
        # now". These are visible within a minute, so the CloudWatch graph
        # doubles as the FinOps view: sum ModelSpendUsd over a period to get
        # what that period cost, and alarm on it well before the monthly budget
        # in terraform/api/monitoring.tf would notice.
        #
        # Tokens are emitted separately because they explain the money. Input
        # dominates on this workload — a tool loop re-sends the whole transcript
        # on every call — so a spend rise with flat output means the loop got
        # longer, not that replies got wordier.
        metrics.add_metric(name="ModelSpendUsd", unit=MetricUnit.NoUnit, value=usd_cost)
        metrics.add_metric(name="InputTokens", unit=MetricUnit.Count, value=input_tokens)
        metrics.add_metric(name="OutputTokens", unit=MetricUnit.Count, value=output_tokens)

        log_context = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "credits_used": f"{credits_used:.6f}",
            # The real figure, so CloudWatch can answer "what did today cost".
            "usd_cost": f"{usd_cost:.6f}",
        }
        if user_id:
            log_context["user_id"] = user_id
        if conversation_id:
            log_context["conversation_id"] = conversation_id

        self.logger.info(
            "Credit calculation: in=%s, out=%s, credits=%.6f",
            input_tokens,
            output_tokens,
            credits_used,
            extra=log_context,
        )

        return round(credits_used, 6)

    def deduct_credits(
        self,
        user_id: str,
        credits_used: float,
        conversation_id: str | None = None,
    ) -> float:
        try:
            key = balance_key(user_id)
            remaining = self.redis.incrbyfloat(key, -credits_used)
            # INCRBYFLOAT on a missing key creates it without a TTL, which would
            # leave an orphan if a period rolled over mid-request.
            self.redis.expire(key, KEY_TTL_SECONDS)

            if remaining is None:
                log_context = {"user_id": user_id, "operation": "deduct_credits"}
                if conversation_id:
                    log_context["conversation_id"] = conversation_id
                self.logger.error(
                    "INCRBYFLOAT returned None for user %s",
                    user_id,
                    extra=log_context,
                )
                return 0.0

            remaining_float = float(remaining)

            log_context = {
                "user_id": user_id,
                "credits_used": f"{credits_used:.6f}",
                "remaining_credits": f"{remaining_float:.6f}",
            }
            if conversation_id:
                log_context["conversation_id"] = conversation_id

            self.logger.info(
                "Deducted %.6f credits from user %s, remaining=%.6f",
                credits_used,
                user_id,
                remaining_float,
                extra=log_context,
            )

            return remaining_float

        except Exception as e:
            log_context = {
                "user_id": user_id,
                "operation": "deduct_credits",
                "credits_used": f"{credits_used:.6f}",
                "error": str(e),
            }
            if conversation_id:
                log_context["conversation_id"] = conversation_id

            self.logger.exception(
                "Redis error during credit deduction for user %s: %s",
                user_id,
                e,
                extra=log_context,
            )
            self.logger.warning(
                "Treating user %s balance as exhausted after Redis error",
                user_id,
                extra=log_context,
            )
            return 0.0
