"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_url import normalize_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="portfolio-ai-api", validation_alias="APP_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    port: int = Field(default=8000, validation_alias="PORT")

    database_url: str = Field(validation_alias="DATABASE_URL")
    alembic_database_url: str = Field(default="", validation_alias="ALEMBIC_DATABASE_URL")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    news_api_key: str = Field(default="", validation_alias="NEWS_API_KEY")
    news_cache_ttl_seconds: int = Field(default=900, validation_alias="NEWS_CACHE_TTL_SECONDS")

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        validation_alias="DEEPSEEK_BASE_URL",
    )
    llm_provider: str = Field(default="openai", validation_alias="LLM_PROVIDER")
    llm_model: str = Field(default="", validation_alias="LLM_MODEL")
    llm_enabled: bool = Field(default=True, validation_alias="LLM_ENABLED")
    llm_cache_ttl_seconds: int = Field(default=3600, validation_alias="LLM_CACHE_TTL_SECONDS")
    brief_cache_ttl_seconds: int = Field(
        default=1800,
        validation_alias="BRIEF_CACHE_TTL_SECONDS",
    )

    redis_url: str = Field(default="", validation_alias="REDIS_URL")
    cache_backend: str = Field(default="memory", validation_alias="CACHE_BACKEND")

    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")

    @field_validator("database_url", "alembic_database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str) and value.strip():
            return normalize_database_url(value)
        return value

    @property
    def migration_database_url(self) -> str:
        """Alembic URL — prefer direct Supabase connection when set."""
        if self.alembic_database_url:
            return self.alembic_database_url
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw or raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]


settings = Settings()
