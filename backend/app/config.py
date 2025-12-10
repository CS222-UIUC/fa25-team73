from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI
    OPENAI_API_KEY: str

    # YouTube Data API
    YOUTUBE_API_KEY: str = ""  # Optional, will use fallback if not set

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Security
    CORS_ORIGINS: str = "chrome-extension://*"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Cache
    CACHE_TTL_SECONDS: int = 604800  # 7 days

    # LLM Configuration
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1000
    CLAIM_CONFIDENCE_THRESHOLD: float = 0.6

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
