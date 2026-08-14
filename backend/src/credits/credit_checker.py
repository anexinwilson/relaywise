from upstash_redis import Redis

from utils import get_logger

from .period import KEY_TTL_SECONDS, STARTING_CREDITS, balance_key

logger = get_logger(__name__)


class CreditChecker:
    """Reads the current month's balance, seeding it on first sight.

    A missing key means "new period", not "exhausted" — treating it as
    exhausted would lock out every user on the first of the month.
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)

    def check_credits(
        self,
        user_id: str,
        conversation_id: str | None = None,
    ) -> tuple[bool, float]:
        key = balance_key(user_id)
        context = {"user_id": user_id}
        if conversation_id:
            context["conversation_id"] = conversation_id

        try:
            balance = self.redis.get(key)

            if balance is None:
                self._seed(key)
                self.logger.info(
                    "Seeded a new credit period for user %s",
                    user_id,
                    extra={**context, "credits": STARTING_CREDITS},
                )
                return True, STARTING_CREDITS

            remaining = float(balance)
            if remaining <= 0:
                self.logger.warning(
                    "User %s has exhausted this period's credits",
                    user_id,
                    extra={**context, "balance": remaining},
                )
                return False, remaining

            return True, remaining

        except Exception as exc:
            # Billing state is a trust boundary: an outage must not authorize an
            # unmetered model call.
            self.logger.exception(
                "Redis error during credit check for user %s: %s",
                user_id,
                exc,
                extra={**context, "operation": "credit_check"},
            )
            return False, 0.0

    def _seed(self, key: str) -> None:
        """SETNX so two concurrent requests cannot both seed and reset a balance
        that the other has already started spending."""
        self.redis.setnx(key, STARTING_CREDITS)
        self.redis.expire(key, KEY_TTL_SECONDS)
