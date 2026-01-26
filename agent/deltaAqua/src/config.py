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
    # Agent-specific settings only
    COMPOSIO_API_KEY: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    GEMINI_COMPILER_MODEL: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str
    PINECONE_CONNECTION_STRING: str

    model_config = SettingsConfigDict(
        env_file=".env.local",
        extra="ignore"  
    )

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Convert relative path to absolute path for GOOGLE_APPLICATION_CREDENTIALS
    if settings.GOOGLE_APPLICATION_CREDENTIALS and not os.path.isabs(settings.GOOGLE_APPLICATION_CREDENTIALS):
        base_dir = Path(__file__).parent.parent
        settings.GOOGLE_APPLICATION_CREDENTIALS = str(base_dir / settings.GOOGLE_APPLICATION_CREDENTIALS)
    return settings

settings = get_settings()