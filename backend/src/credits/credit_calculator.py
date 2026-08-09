from upstash_redis import Redis

from utils import get_logger

logger = get_logger(__name__)


def extract_token_counts(result: dict) -> tuple[int, int]:
    messages = result.get("messages", [])
    ai_messages = [
        m for m in messages if hasattr(m, "usage_metadata") and m.usage_metadata
    ]

    if not ai_messages:
        logger.error("No usage_metadata found in any AI message")
        return 0, 0

    input_tokens = ai_messages[-1].usage_metadata.get("input_tokens", 0)
    output_tokens = sum(m.usage_metadata.get("output_tokens", 0) for m in ai_messages)

    return input_tokens, output_tokens


class CreditCalculator:
    INPUT_COST_PER_1M = 60.0
    OUTPUT_COST_PER_1M = 480.0

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

        log_context = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "credits_used": f"{credits_used:.6f}",
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
            key = f"user_credits:{user_id}"
            remaining = self.redis.incrbyfloat(key, -credits_used)

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
