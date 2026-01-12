from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str
    COMPOSIO_API_KEY: str
    GOOGLE_VERTEX_API_KEY: str
    GEMINI_COMPILER_MODEL: str 

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()