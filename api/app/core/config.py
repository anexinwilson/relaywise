"""Runtime configuration.

In Lambda the values come from one JSON secret in Secrets Manager. Locally they
come from the process environment, so `uvicorn` can run without AWS access.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_ID = "relaywise/lambda/secrets"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    AWS_REGION: str = "us-east-1"
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    CLERK_DOMAIN: str
    DATABASE_URL: str
    SQS_QUEUE_URL: str


def _secret_values() -> dict:
    """Secrets Manager payload, or an empty mapping outside Lambda."""
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return {}

    secret_id = os.getenv("SECRETS_MANAGER_SECRET_ID", DEFAULT_SECRET_ID)
    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except Exception as exc:  # noqa: BLE001 - surfaced as a startup failure
        raise RuntimeError(f"Failed to retrieve secret {secret_id}") from exc
    return json.loads(response["SecretString"])


@lru_cache
def get_settings() -> Settings:
    """Cached settings. Environment wins over the secret so a Lambda env var
    can override a single key without editing the secret."""
    secret = _secret_values()
    environment = {key: value for key, value in os.environ.items() if key.isupper()}
    return Settings(**{**secret, **environment})


settings = get_settings()
