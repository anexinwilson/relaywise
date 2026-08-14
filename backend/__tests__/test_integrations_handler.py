"""The control plane's auth boundary and dispatch.

The action this replaces trusted a `userId` sent in a request body. These tests
pin the rule that identity now comes only from the authorizer.
"""

import sys
import types

import pytest

# agent.sync pulls in the Composio SDK at import time; stub it so these tests
# stay fast and offline.
_stub = types.ModuleType("agent.sync")
_stub.get_auth_url = None
_stub.sync_connections_to_redis = None
_stub.disconnect_app = None
_stub.check_app_limit = lambda *a, **k: False
sys.modules.setdefault("agent.sync", _stub)

# `integrations.handler` is a module; `integrations.__init__` re-exports a
# function of the same name, so import the module explicitly.
import integrations.handler as integrations  # noqa: E402


class LambdaContext:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:test"
    aws_request_id = "test-request"


CONTEXT = LambdaContext()
AUTHENTICATED = {"resolverContext": {"userId": "user_123"}}


def _event(field: str, arguments: dict | None = None, identity: dict | None = None) -> dict:
    return {
        "info": {"fieldName": field},
        "arguments": arguments or {},
        "identity": AUTHENTICATED if identity is None else identity,
    }


def test_every_field_has_a_resolver() -> None:
    assert set(integrations.RESOLVERS) == {"connectApp", "syncConnections", "disconnectApp"}


def test_unknown_field_is_reported_not_ignored() -> None:
    result = integrations.handler(_event("nope"), CONTEXT)

    assert result == {"success": False, "error": "Unknown field: nope"}


def test_missing_identity_is_rejected() -> None:
    result = integrations.handler(_event("syncConnections", identity={}), CONTEXT)

    assert result == {"success": False, "error": "Unauthorized"}


def test_user_id_is_never_read_from_arguments() -> None:
    """A client supplying userId must not be able to act as another user."""
    result = integrations.handler(
        _event("syncConnections", arguments={"userId": "someone_else"}, identity={}),
        CONTEXT,
    )

    assert result == {"success": False, "error": "Unauthorized"}


def test_identity_from_request_headers_is_accepted() -> None:
    """Some APPSYNC_JS resolvers forward resolverContext as request.headers."""
    event = {
        "info": {"fieldName": "syncConnections"},
        "arguments": {},
        "request": {"headers": {"userId": "user_456"}},
    }

    assert integrations._user_id(event) == "user_456"


def test_connect_requires_a_slug() -> None:
    result = integrations.handler(_event("connectApp"), CONTEXT)

    assert result["success"] is False
    assert "slug" in result["error"]


def test_disconnect_requires_a_slug() -> None:
    result = integrations.handler(_event("disconnectApp"), CONTEXT)

    assert result["success"] is False
    assert "slug" in result["error"]


def test_resolver_failure_is_contained(monkeypatch) -> None:
    def explode(user_id, arguments):
        raise RuntimeError("composio unreachable")

    monkeypatch.setitem(integrations.RESOLVERS, "syncConnections", explode)

    result = integrations.handler(_event("syncConnections"), CONTEXT)

    assert result == {"success": False, "error": "composio unreachable"}


def test_connect_is_refused_at_the_app_limit(monkeypatch) -> None:
    """The UI shows a limit too, but a client-side check is advisory only."""
    monkeypatch.setattr(integrations, "check_app_limit", lambda user_id, limit: True)

    result = integrations.handler(_event("connectApp", {"slug": "gmail"}), CONTEXT)

    assert result["success"] is False
    assert str(integrations.MAX_CONNECTED_APPS) in result["error"]


def test_unreachable_cache_is_unknown_not_empty() -> None:
    """An outage must not be reported as "you have connected nothing".

    Returning [] would make the caller tell every user their account is empty
    while Redis is down. None means "ask the agent anyway".
    """
    import agent.sync as sync_module

    class Boom:
        def hkeys(self, *_):
            raise RuntimeError("redis down")

    import unittest.mock as mock

    with mock.patch.object(sync_module, "get_redis_client", lambda: Boom()):
        assert sync_module.connected_slugs("user_1") is None


def test_empty_account_is_reported_as_empty() -> None:
    import agent.sync as sync_module
    import unittest.mock as mock

    class Empty:
        def hkeys(self, *_):
            return []

    with mock.patch.object(sync_module, "get_redis_client", lambda: Empty()):
        assert sync_module.connected_slugs("user_1") == []
