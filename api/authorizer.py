"""AppSync Lambda authorizer.

Verifies a Clerk-issued JWT against Clerk's JWKS and returns the subject as
`resolverContext.userId`. Every resolver treats that value as the only trusted
source of identity — arguments from the client are never used for authorization.

Deployed as its own Lambda from `Dockerfile.authorizer`, which packages *only
this file*. It therefore must not import from the `app` package: doing so
raises ModuleNotFoundError at cold start and AppSync then denies every request.
Keep this module dependency-free apart from third-party libraries.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3
import jwt
from aws_lambda_powertools import Logger, Metrics
from jwt import PyJWKClient

logger = Logger(service="relaywise-authorizer")
metrics = Metrics(namespace="Relaywise", service="authorizer")

DEFAULT_SECRET_ID = "relaywise/lambda/secrets"
DENY: dict[str, Any] = {"isAuthorized": False, "context": {}}
AUTH_TTL_SECONDS = 300
BEARER_PREFIX = "Bearer "


@lru_cache(maxsize=1)
def _clerk_domain() -> str:
    """Read once per container; this runs on every AppSync request."""
    secret_id = os.getenv("SECRETS_MANAGER_SECRET_ID", DEFAULT_SECRET_ID)
    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
    secret = json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
    return secret["CLERK_DOMAIN"]


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    return PyJWKClient(f"https://{_clerk_domain()}/.well-known/jwks.json")


@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context

    authorization = event.get("authorizationToken", "")
    if not authorization.startswith(BEARER_PREFIX):
        metrics.add_metric(name="AuthDenied", unit="Count", value=1)
        return DENY

    token = authorization[len(BEARER_PREFIX) :]
    try:
        domain = _clerk_domain()
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=f"https://{domain}",
        )
    except jwt.InvalidTokenError:
        # Base class for expiry, bad signature, and issuer mismatch.
        metrics.add_metric(name="AuthDenied", unit="Count", value=1)
        return DENY
    except Exception as exc:  # noqa: BLE001 - a JWKS outage must still deny
        metrics.add_metric(name="AuthError", unit="Count", value=1)
        logger.exception("Authorizer failed", error_type=type(exc).__name__)
        return DENY

    metrics.add_metric(name="AuthAccepted", unit="Count", value=1)
    return {
        "isAuthorized": True,
        "resolverContext": {"userId": claims.get("sub")},
        "ttlOverride": AUTH_TTL_SECONDS,
    }
