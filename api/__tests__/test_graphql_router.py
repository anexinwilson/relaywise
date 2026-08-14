from app.graphql import router
from app.graphql.context import UnauthorizedError

AUTHENTICATED = {"resolverContext": {"userId": "user_123"}}


def _event(field_name: str, arguments: dict | None = None, identity: dict | None = None) -> dict:
    return {
        "info": {"fieldName": field_name},
        "arguments": arguments or {},
        "identity": identity if identity is not None else AUTHENTICATED,
    }


def test_every_registered_field_is_callable() -> None:
    assert all(callable(resolver) for resolver in router.RESOLVERS.values())


def test_unknown_object_field_returns_error_shape() -> None:
    result = router.dispatch(_event("noSuchField"))

    assert result == {"success": False, "error": "Unknown field: noSuchField"}


def test_unknown_list_field_returns_empty_list() -> None:
    """List-typed fields degrade to [] so the UI renders empty, not broken."""
    assert "getUserConversations" in router.LIST_FIELDS
    assert router.dispatch(_event("getUserConversations", identity={})) == []


def test_unauthorized_object_field_returns_error(monkeypatch) -> None:
    def unauthorized(_request):
        raise UnauthorizedError

    monkeypatch.setitem(router.RESOLVERS, "askAgent", unauthorized)

    assert router.dispatch(_event("askAgent")) == {
        "success": False,
        "error": "Unauthorized",
    }


def test_resolver_exception_is_contained(monkeypatch) -> None:
    """A resolver blowing up must not surface as a Lambda error to AppSync."""

    def explode(_request):
        raise RuntimeError("database on fire")

    monkeypatch.setitem(router.RESOLVERS, "deleteConversation", explode)

    assert router.dispatch(_event("deleteConversation")) == {
        "success": False,
        "error": "database on fire",
    }


def test_delete_conversation_is_registered() -> None:
    """Regression: the field existed in the GraphQL schema but had no resolver,
    so every delete silently failed."""
    assert "deleteConversation" in router.RESOLVERS
