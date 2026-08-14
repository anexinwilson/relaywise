import pytest

from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import Mock

from credits import STARTING_CREDITS, balance_key, current_period
from credits.credit_calculator import CreditCalculator, extract_token_counts
from credits.credit_checker import CreditChecker


@dataclass
class Message:
    usage_metadata: dict[str, int] | None = None


def test_sums_tokens_across_every_model_call() -> None:
    """A tool-using turn bills once per model call, not once per turn."""
    result = {
        "messages": [
            Message({"input_tokens": 120, "output_tokens": 10}),
            Message({"input_tokens": 180, "output_tokens": 20}),
        ]
    }

    assert extract_token_counts(result) == (300, 30)


def test_multi_step_runs_are_not_undercharged() -> None:
    """Regression: input used to be read from the last call only.

    A three-call tool loop re-sends the ~3,600-token schema each time, so
    counting one call charged for roughly a third of the real spend.
    """
    schema_cost = 3_600
    result = {
        "messages": [
            Message({"input_tokens": schema_cost, "output_tokens": 30}),
            Message({"input_tokens": schema_cost + 400, "output_tokens": 25}),
            Message({"input_tokens": schema_cost + 900, "output_tokens": 60}),
        ]
    }

    input_tokens, output_tokens = extract_token_counts(result)

    assert input_tokens == 3_600 + 4_000 + 4_500
    assert output_tokens == 115
    # The old behaviour would have reported only the final call.
    assert input_tokens > 4_500


def test_no_usage_metadata_is_not_charged() -> None:
    assert extract_token_counts({"messages": []}) == (0, 0)
    assert extract_token_counts({"messages": [Message(None)]}) == (0, 0)


def test_credit_calculation_clamps_invalid_negative_usage() -> None:
    """Negative counts are treated as zero, never as a refund.

    Asserted against the rate rather than a literal, so changing the model's
    price does not require editing this test.
    """
    calculator = CreditCalculator(Mock())
    expected = 1_000 / 1_000_000 * CreditCalculator.OUTPUT_COST_PER_1M

    assert calculator.calculate_credits(-100, 1_000) == pytest.approx(expected)
    assert calculator.calculate_credits(-100, -100) == 0.0


# --- monthly period ---------------------------------------------------------


def test_period_is_the_calendar_month() -> None:
    moment = datetime(2026, 8, 11, 23, 59, tzinfo=timezone.utc)

    assert current_period(moment) == "2026-08"
    assert balance_key("user_1", moment) == "user_credits:user_1:2026-08"


def test_period_rolls_over_without_a_scheduler() -> None:
    """The allowance resets because the key changes, not because anything ran."""
    august = datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc)
    september = datetime(2026, 9, 1, 0, 1, tzinfo=timezone.utc)

    assert balance_key("user_1", august) != balance_key("user_1", september)


# --- checking ---------------------------------------------------------------


def test_first_request_of_a_period_seeds_a_full_balance() -> None:
    redis = Mock()
    redis.get.return_value = None

    allowed, remaining = CreditChecker(redis).check_credits("user_1")

    assert (allowed, remaining) == (True, STARTING_CREDITS)
    redis.setnx.assert_called_once()
    redis.expire.assert_called_once()


def test_seeding_uses_setnx_so_concurrent_requests_cannot_reset_a_balance() -> None:
    redis = Mock()
    redis.get.return_value = None

    CreditChecker(redis).check_credits("user_1")

    key, value = redis.setnx.call_args[0]
    assert key == balance_key("user_1")
    assert value == STARTING_CREDITS


def test_positive_balance_is_allowed() -> None:
    redis = Mock()
    redis.get.return_value = "2.5"

    assert CreditChecker(redis).check_credits("user_1") == (True, 2.5)


def test_exhausted_balance_is_refused() -> None:
    redis = Mock()
    redis.get.return_value = "0"

    allowed, remaining = CreditChecker(redis).check_credits("user_1")

    assert allowed is False
    assert remaining == 0.0


def test_credit_check_fails_closed_when_redis_is_unavailable() -> None:
    """An outage must not authorize an unmetered model call."""
    redis = Mock()
    redis.get.side_effect = RuntimeError("unavailable")

    assert CreditChecker(redis).check_credits("user_1") == (False, 0.0)


# --- deducting --------------------------------------------------------------


def test_deduction_targets_the_current_period_key() -> None:
    redis = Mock()
    redis.incrbyfloat.return_value = "97.5"

    remaining = CreditCalculator(redis).deduct_credits("user_1", 2.5)

    key, delta = redis.incrbyfloat.call_args[0]
    assert key == balance_key("user_1")
    assert delta == -2.5
    assert remaining == 97.5


def test_deduction_refreshes_the_ttl_so_no_orphan_key_is_left() -> None:
    redis = Mock()
    redis.incrbyfloat.return_value = "97.5"

    CreditCalculator(redis).deduct_credits("user_1", 2.5)

    redis.expire.assert_called_once()


# --- pricing calibration ----------------------------------------------------


def test_monthly_allowance_is_worth_a_fixed_amount() -> None:
    """The one invariant: a full allowance costs ALLOWANCE_USD of model spend.

    If this breaks, the credit rates and the model's price have drifted apart
    and the allowance no longer means what the landing page says.
    """
    from credits.pricing import ALLOWANCE_USD, CREDIT_VALUE_USD

    assert STARTING_CREDITS * CREDIT_VALUE_USD == ALLOWANCE_USD


def test_credits_and_dollars_agree() -> None:
    """Spending N credits must cost N * CREDIT_VALUE_USD, whatever the rates."""
    from unittest.mock import Mock

    from credits.pricing import CREDIT_VALUE_USD, usd_for_tokens

    calculator = CreditCalculator(Mock())
    credits = calculator.calculate_credits(3509, 11)
    dollars = usd_for_tokens(3509, 11)

    assert credits * CREDIT_VALUE_USD == pytest.approx(dollars, rel=1e-9)


def test_rates_are_derived_not_hardcoded() -> None:
    """Changing the model price must move the credit rates with it."""
    from credits.pricing import INPUT_USD_PER_1M, OUTPUT_USD_PER_1M, credits_per_1m

    assert CreditCalculator.INPUT_COST_PER_1M == credits_per_1m(INPUT_USD_PER_1M)
    assert CreditCalculator.OUTPUT_COST_PER_1M == credits_per_1m(OUTPUT_USD_PER_1M)


def test_reset_date_rolls_into_the_next_year_in_december() -> None:
    """December must reset to 1 January of the following year, not month 13."""
    from datetime import datetime, timezone

    from credits.period import next_reset, next_reset_label

    december = datetime(2026, 12, 14, tzinfo=timezone.utc)

    assert next_reset(december) == datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert next_reset_label(december) == "1 January 2027"


def test_reset_label_matches_the_key_the_balance_rolls_over_on() -> None:
    """The date shown to the user must be the date the period key changes."""
    from datetime import datetime, timezone

    from credits.period import current_period, next_reset, next_reset_label

    now = datetime(2026, 8, 15, tzinfo=timezone.utc)

    assert current_period(now) == "2026-08"
    assert current_period(next_reset(now)) == "2026-09"
    assert next_reset_label(now) == "1 September 2026"
