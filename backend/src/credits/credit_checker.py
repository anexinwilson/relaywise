from upstash_redis import Redis

from utils import get_logger

logger = get_logger(__name__)


class CreditChecker:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)

    def check_credits(
        self,
        user_id: str,
        conversation_id: str | None = None,
    ) -> tuple[bool, float]:
        try:
            key = f"user_credits:{user_id}"
            balance = self.redis.get(key)

            if balance is None:
                # Key doesn't exist - credits not initialized or expired
                log_context = {"user_id": user_id}
                if conversation_id:
                    log_context["conversation_id"] = conversation_id
                self.logger.warning(
                    "No credit key found for user %s", user_id, extra=log_context
                )
                return False, 0.0

            balance_float = float(balance)
            has_credits = balance_float > 0

            if not has_credits:
                log_context = {"user_id": user_id, "balance": balance_float}
                if conversation_id:
                    log_context["conversation_id"] = conversation_id
                self.logger.warning(
                    "User %s has exhausted credits: %s",
                    user_id,
                    balance_float,
                    extra=log_context,
                )

            return has_credits, balance_float

        except Exception as e:
            # Log Redis error at ERROR level with full context
            log_context = {
                "user_id": user_id,
                "operation": "credit_check",
                "error": str(e),
            }
            if conversation_id:
                log_context["conversation_id"] = conversation_id
            self.logger.exception(
                "Redis error during credit check for user %s: %s",
                user_id,
                e,
                extra=log_context,
            )
            # Billing state is a trust boundary: an outage must not authorize an
            # unmetered model call.
            self.logger.warning(
                "Denying model execution for user %s because credits could not "
                "be verified",
                user_id,
                extra=log_context,
            )
            return False, 0.0
