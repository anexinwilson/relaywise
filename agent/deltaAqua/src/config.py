from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Settings(BaseSettings):
    COMPOSIO_API_KEY: str
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    # GOOGLE_APPLICATION_CREDENTIALS: str
    GEMINI_COMPILER_MODEL: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str
    PINECONE_CONNECTION_STRING: str
    CALLBACK_URL: str
    AWS_REGION: str = 'us-east-1'
    BEDROCK_MODEL_ID: str
    AGENTCORE_MEMORY_ID: str

    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

# @lru_cache
# def get_settings() -> Settings:
#     settings = Settings()
#     if settings.GOOGLE_APPLICATION_CREDENTIALS and not os.path.isabs(settings.GOOGLE_APPLICATION_CREDENTIALS):
#         base_dir = Path(__file__).parent.parent
#         settings.GOOGLE_APPLICATION_CREDENTIALS = str(base_dir / settings.GOOGLE_APPLICATION_CREDENTIALS)
#     return settings

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()