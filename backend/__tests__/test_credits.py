from dataclasses import dataclass
from unittest.mock import Mock

from credits.credit_calculator import CreditCalculator, extract_token_counts
from credits.credit_checker import CreditChecker


@dataclass
class Message:
    usage_metadata: dict[str, int] | None = None


def test_extracts_last_input_context_and_all_generated_tokens() -> None:
    result = {
        "messages": [
            Message({"input_tokens": 120, "output_tokens": 10}),
            Message({"input_tokens": 180, "output_tokens": 20}),
        ]
    }

    assert extract_token_counts(result) == (180, 30)


def test_credit_calculation_clamps_invalid_negative_usage() -> None:
    calculator = CreditCalculator(Mock())

    assert calculator.calculate_credits(-100, 1_000) == 0.48


def test_credit_check_requires_a_positive_stored_balance() -> None:
    redis = Mock()
    redis.get.return_value = "2.5"

    assert CreditChecker(redis).check_credits("user-1") == (True, 2.5)


def test_credit_check_fails_closed_when_redis_is_unavailable() -> None:
    redis = Mock()
    redis.get.side_effect = RuntimeError("unavailable")

    assert CreditChecker(redis).check_credits("user-1") == (False, 0.0)
