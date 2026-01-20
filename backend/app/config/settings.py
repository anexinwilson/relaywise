from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

class Settings(BaseSettings):
    DATABASE_URL: str
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str
    COMPOSIO_API_KEY: str
    GOOGLE_VERTEX_API_KEY: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    GEMINI_COMPILER_MODEL: str 
    COMPOSIO_MCP_CONFIG_ID: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str
    PINECONE_CONNECTION_STRING: str
    logging.basicConfig(
    level=logging.INFO,  
    format='[%(asctime)s][%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
    
)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()