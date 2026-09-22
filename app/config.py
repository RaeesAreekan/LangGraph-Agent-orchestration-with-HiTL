from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Mounting configuration for the application, including database and API keys.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/orchestrator"
    )
    redis_url: str = "redis://localhost:6379/0"
    chroma_url: str = "http://localhost:8001"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    supervisor_model: str = "gpt-4o-mini"
    specialist_model: str = "gpt-4o-mini"
    reviewer_model: str = "gpt-4o-mini"

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "agent-orchestrator"
    langsmith_endpoint: str = "https://api.smith.langchain.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()