import json
from utils import get_logger

logger = get_logger(__name__)


class CreditLogger:
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def log_usage(
        self,
        user_id: str,
        conversation_id: str,
        input_tokens: int,
        output_tokens: int,
        credits_used: float,
        remaining_credits: float
    ):

        log_data = {
            "event": "credit_usage",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "credits_used": f"{credits_used:.6f}",
            "remaining_credits": f"{remaining_credits:.6f}"
        }
        
        self.logger.info(json.dumps(log_data))
        
        # Warn if credits exhausted
        if remaining_credits <= 0:
            self.logger.warning(
                f"User {user_id} has exhausted credits: {remaining_credits:.6f}"
            )
