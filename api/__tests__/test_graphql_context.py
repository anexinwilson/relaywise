import pytest

from app.graphql.context import AppSyncRequest, UnauthorizedError


def test_reads_identity_from_resolver_context() -> None:
    request = AppSyncRequest.from_event(
        {
            "info": {"fieldName": "askAgent"},
            "arguments": {"message": "hi"},
            "identity": {"resolverContext": {"userId": "user_123"}},
        }
    )

    assert request.field_name == "askAgent"
    assert request.user_id == "user_123"
    assert request.arguments == {"message": "hi"}


def test_reads_identity_from_request_headers() -> None:
    """Several APPSYNC_JS resolvers forward resolverContext as request.headers."""
    request = AppSyncRequest.from_event(
        {
            "info": {"fieldName": "getUserConversations"},
            "arguments": {},
            "request": {"headers": {"userId": "user_456"}},
        }
    )

    assert request.user_id == "user_456"


def test_unwraps_nested_payload() -> None:
    request = AppSyncRequest.from_event(
        {"payload": {"info": {"fieldName": "askAgent"}, "arguments": {"message": "hi"}}}
    )

    assert request.field_name == "askAgent"


def test_missing_identity_yields_no_user() -> None:
    request = AppSyncRequest.from_event({"info": {"fieldName": "askAgent"}})

    assert request.user_id is None
    with pytest.raises(UnauthorizedError):
        request.require_user_id()


def test_client_arguments_cannot_supply_identity() -> None:
    """userId is only ever trusted from the authorizer, never from arguments."""
    request = AppSyncRequest.from_event(
        {
            "info": {"fieldName": "getUserConversations"},
            "arguments": {"userId": "attacker"},
        }
    )

    assert request.user_id is None
