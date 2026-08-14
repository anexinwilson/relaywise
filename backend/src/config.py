from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os
import boto3

# No logging.basicConfig here: it attaches a plain-text handler to the root
# logger, which in Lambda duplicates every record alongside the Powertools JSON
# handler and breaks log parsing. Telemetry is owned by observability.telemetry.


class Settings(BaseSettings):
    COMPOSIO_API_KEY: str
    CALLBACK_URL: str
    AWS_REGION: str = 'us-east-1'
    BEDROCK_MANTLE_BASE_URL: str
    BEDROCK_MANTLE_API_KEY: str
    BEDROCK_MODEL_ID: str
    DATABASE_URL: str
    APPSYNC_EVENTS_ENDPOINT: str
    APPSYNC_API_KEY: str
    SQS_QUEUE_URL: str
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str

    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")


def _secret_values() -> dict:
    """Load deployment secrets in Lambda; local development uses `.env.local`."""
    secret_id = os.getenv("SECRETS_MANAGER_SECRET_ID", "relaywise/lambda/secrets")
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return {}
    response = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1")).get_secret_value(
        SecretId=secret_id
    )
    return json.loads(response["SecretString"])

@lru_cache
def get_settings() -> Settings:
    secret = _secret_values()
    environment = {key: value for key, value in os.environ.items() if key.isupper()}
    merged = {**secret, **environment}
    return Settings(**merged)

settings = get_settings()
