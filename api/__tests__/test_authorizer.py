from unittest.mock import Mock

import jwt

import authorizer


class LambdaContext:
    function_name = "test-authorizer"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:test"
    aws_request_id = "test-request"


CONTEXT = LambdaContext()


def test_rejects_missing_bearer_token() -> None:
    assert authorizer.lambda_handler({}, CONTEXT) == {
        "isAuthorized": False,
        "context": {},
    }


def test_authorizes_valid_clerk_subject(monkeypatch) -> None:
    signing_key = Mock(key="public-key")
    jwks_client = Mock()
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    monkeypatch.setattr(authorizer, "get_clerk_domain", lambda: "clerk.example.com")
    monkeypatch.setattr(authorizer, "get_jwks_client", lambda: jwks_client)
    monkeypatch.setattr(
        authorizer.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user_123"},
    )

    result = authorizer.lambda_handler(
        {"authorizationToken": "Bearer signed-token"},
        CONTEXT,
    )

    assert result == {
        "isAuthorized": True,
        "resolverContext": {"userId": "user_123"},
        "ttlOverride": 300,
    }
    jwks_client.get_signing_key_from_jwt.assert_called_once_with("signed-token")


def test_rejects_invalid_token(monkeypatch) -> None:
    signing_key = Mock(key="public-key")
    jwks_client = Mock()
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    monkeypatch.setattr(authorizer, "get_clerk_domain", lambda: "clerk.example.com")
    monkeypatch.setattr(authorizer, "get_jwks_client", lambda: jwks_client)

    def reject_token(*args, **kwargs):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(authorizer.jwt, "decode", reject_token)

    assert authorizer.lambda_handler(
        {"authorizationToken": "Bearer invalid-token"},
        CONTEXT,
    ) == {"isAuthorized": False, "context": {}}
