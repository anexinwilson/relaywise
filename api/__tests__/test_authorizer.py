from unittest.mock import Mock

import jwt
import pytest

import authorizer


class LambdaContext:
    function_name = "test-authorizer"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:test"
    aws_request_id = "test-request"


CONTEXT = LambdaContext()


@pytest.fixture
def jwks_client(monkeypatch):
    """Stub out Clerk's JWKS endpoint and the Secrets Manager lookup."""
    client = Mock()
    client.get_signing_key_from_jwt.return_value = Mock(key="public-key")
    monkeypatch.setattr(authorizer, "_clerk_domain", lambda: "clerk.example.com")
    monkeypatch.setattr(authorizer, "_jwks_client", lambda: client)
    return client


def test_rejects_missing_bearer_token() -> None:
    assert authorizer.lambda_handler({}, CONTEXT) == authorizer.DENY


def test_rejects_token_without_bearer_prefix() -> None:
    assert authorizer.lambda_handler({"authorizationToken": "signed"}, CONTEXT) == authorizer.DENY


def test_authorizes_valid_clerk_subject(monkeypatch, jwks_client) -> None:
    monkeypatch.setattr(authorizer.jwt, "decode", lambda *a, **k: {"sub": "user_123"})

    result = authorizer.lambda_handler({"authorizationToken": "Bearer signed-token"}, CONTEXT)

    assert result == {
        "isAuthorized": True,
        "resolverContext": {"userId": "user_123"},
        "ttlOverride": 300,
    }
    jwks_client.get_signing_key_from_jwt.assert_called_once_with("signed-token")


def test_rejects_invalid_token(monkeypatch, jwks_client) -> None:
    def reject(*args, **kwargs):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(authorizer.jwt, "decode", reject)

    assert (
        authorizer.lambda_handler({"authorizationToken": "Bearer bad"}, CONTEXT)
        == authorizer.DENY
    )


def test_denies_when_jwks_lookup_fails(monkeypatch) -> None:
    """A JWKS or Secrets Manager outage must deny, never fail open."""

    def explode():
        raise RuntimeError("jwks unavailable")

    monkeypatch.setattr(authorizer, "_clerk_domain", explode)

    assert (
        authorizer.lambda_handler({"authorizationToken": "Bearer token"}, CONTEXT)
        == authorizer.DENY
    )


def test_authorizer_does_not_import_app_package() -> None:
    """Dockerfile.authorizer packages only this module.

    Importing from `app` would raise ModuleNotFoundError at cold start and
    AppSync would then deny every request in the system.
    """
    source = (authorizer.__file__ or "").replace(".pyc", ".py")
    with open(source, encoding="utf-8") as handle:
        body = handle.read()

    assert "from app." not in body
    assert "import app" not in body
