from datetime import datetime, timezone
from unittest.mock import Mock

from app.services import credits


def test_period_is_the_calendar_month() -> None:
    moment = datetime(2026, 8, 11, 23, 59, tzinfo=timezone.utc)

    assert credits.current_period(moment) == "2026-08"
    assert credits.balance_key("user_1", moment) == "user_credits:user_1:2026-08"


def test_key_matches_the_worker_format() -> None:
    """The worker deducts against this exact key. A mismatch would silently
    mean the API checks one balance while the worker spends another."""
    assert credits.balance_key("user_1", datetime(2026, 1, 5, tzinfo=timezone.utc)) == (
        "user_credits:user_1:2026-01"
    )


def test_new_period_seeds_and_allows(monkeypatch) -> None:
    redis = Mock()
    redis.get.return_value = None
    monkeypatch.setattr(credits, "get_redis", lambda: redis)

    assert credits.check_credits("user_1") == (True, credits.STARTING_CREDITS)
    redis.setnx.assert_called_once()
    redis.expire.assert_called_once()


def test_positive_balance_allows(monkeypatch) -> None:
    redis = Mock()
    redis.get.return_value = "42.5"
    monkeypatch.setattr(credits, "get_redis", lambda: redis)

    assert credits.check_credits("user_1") == (True, 42.5)


def test_zero_balance_refuses(monkeypatch) -> None:
    redis = Mock()
    redis.get.return_value = "0"
    monkeypatch.setattr(credits, "get_redis", lambda: redis)

    allowed, _ = credits.check_credits("user_1")
    assert allowed is False


def test_redis_outage_fails_closed(monkeypatch) -> None:
    redis = Mock()
    redis.get.side_effect = RuntimeError("unavailable")
    monkeypatch.setattr(credits, "get_redis", lambda: redis)

    assert credits.check_credits("user_1") == (False, 0.0)


def test_reset_label_is_the_date_the_period_key_rolls_over() -> None:
    """The date shown must be when the balance actually returns."""
    from datetime import datetime, timezone

    from app.services.credits import current_period, next_reset, next_reset_label

    now = datetime(2026, 8, 15, tzinfo=timezone.utc)

    assert current_period(now) == "2026-08"
    assert current_period(next_reset(now)) == "2026-09"
    assert next_reset_label(now) == "1 September 2026"


def test_reset_label_rolls_into_the_next_year_in_december() -> None:
    from datetime import datetime, timezone

    from app.services.credits import next_reset_label

    assert next_reset_label(datetime(2026, 12, 14, tzinfo=timezone.utc)) == "1 January 2027"


def test_refusal_message_matches_the_worker_wording() -> None:
    """The API and worker ship separately; this catches the two drifting."""
    from app.graphql.resolvers.agent import OUT_OF_CREDITS_MESSAGE

    assert "free credits" in OUT_OF_CREDITS_MESSAGE
    assert "{reset_date}" in OUT_OF_CREDITS_MESSAGE
