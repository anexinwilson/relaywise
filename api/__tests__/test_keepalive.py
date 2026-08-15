"""Event routing for the scheduled keepalive.

One Lambda serves three callers now, so the only thing that can go wrong
quietly is a scheduled event being mistaken for one of the other two and
parsed as a malformed HTTP request.
"""

import handler


def test_scheduled_event_is_recognised() -> None:
    assert handler._is_keepalive_event({"detail-type": "relaywise.keepalive"})


def test_appsync_payload_is_not_mistaken_for_a_schedule() -> None:
    event = {"info": {"fieldName": "askAgent"}, "arguments": {}}
    assert not handler._is_keepalive_event(event)
    assert handler._is_appsync_event(event)


def test_http_request_is_not_mistaken_for_a_schedule() -> None:
    event = {"requestContext": {"http": {"method": "POST"}}, "rawPath": "/health"}
    assert not handler._is_keepalive_event(event)
    assert not handler._is_appsync_event(event)


def test_keepalive_reports_each_store_independently(monkeypatch) -> None:
    """One store being down must not hide the state of the other."""
    from app.services import keepalive

    class BrokenRedis:
        def get(self, _key):
            raise ConnectionError("unreachable")

    monkeypatch.setattr(keepalive, "get_redis", lambda: BrokenRedis())
    monkeypatch.setattr(
        keepalive, "get_session_factory", lambda: (_ for _ in ()).throw(RuntimeError("no db"))
    )

    result = keepalive.touch_stores()

    assert result["healthy"] is False
    assert "RuntimeError" in result["postgres"]
    assert "ConnectionError" in result["redis"]
