import json
import boto3
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_secret():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    try:
        response = client.get_secret_value(SecretId='cognive/lambda/secrets')
        return json.loads(response['SecretString'])
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secrets: {str(e)}")

class Settings(BaseSettings):
    DATABASE_URL: str
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str
    CLERK_DOMAIN: str
    AGENTCORE_MEMORY_ID: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception:
        secret = get_secret()
        return Settings(**secret)

settings = get_settings()