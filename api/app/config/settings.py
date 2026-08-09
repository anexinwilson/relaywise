import json
import boto3
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_secret():
    client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    try:
        response = client.get_secret_value(
            SecretId=os.getenv("SECRETS_MANAGER_SECRET_ID", "cognive/lambda/secrets")
        )
        return json.loads(response['SecretString'])
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secrets: {str(e)}")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    AWS_REGION: str = "us-east-1"
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    CLERK_DOMAIN: str
    DATABASE_URL: str
    SQS_QUEUE_URL: str

@lru_cache
def get_settings() -> Settings:
    secret = get_secret() if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else {}
    return Settings(**secret)

settings = get_settings()
