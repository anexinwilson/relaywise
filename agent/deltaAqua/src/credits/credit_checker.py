from typing import Tuple
from upstash_redis import Redis
from utils import get_logger

logger = get_logger(__name__)


class CreditChecker:
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)
    
    def check_credits(self, user_id: str, conversation_id: str = None) -> Tuple[bool, float]:
        try:
            key = f"user_credits:{user_id}"
            balance = self.redis.get(key)
            
            if balance is None:
                # Key doesn't exist - credits not initialized or expired
                log_context = {"user_id": user_id}
                if conversation_id:
                    log_context["conversation_id"] = conversation_id
                self.logger.warning(
                    f"No credit key found for user {user_id}",
                    extra=log_context
                )
                return False, 0.0
            
            balance_float = float(balance)
            has_credits = balance_float > 0
            
            if not has_credits:
                log_context = {"user_id": user_id, "balance": balance_float}
                if conversation_id:
                    log_context["conversation_id"] = conversation_id
                self.logger.warning(
                    f"User {user_id} has exhausted credits: {balance_float}",
                    extra=log_context
                )
            
            return has_credits, balance_float
            
        except Exception as e:
            # Log Redis error at ERROR level with full context
            log_context = {
                "user_id": user_id,
                "operation": "credit_check",
                "error": str(e)
            }
            if conversation_id:
                log_context["conversation_id"] = conversation_id
            self.logger.error(
                f"Redis error during credit check for user {user_id}: {e}",
                extra=log_context,
                exc_info=True
            )
            # Fail-open: allow execution on Redis errors
            self.logger.warning(
                f"Falling back to default credits (100.0) for user {user_id} due to Redis error",
                extra=log_context
            )
            return True, 100.0
