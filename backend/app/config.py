import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


SIMULATIVE = False


class Settings(BaseSettings):
    """Runtime configuration.

    Production deployments are expected to point DATABASE_URL at PostgreSQL.
    The local default keeps the MVP self-testable without external services.
    """

    app_name: str = "CompeteScope AI"
    environment: str = "development"
    database_url: str = "sqlite:///./competescope.db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    serper_api_key: str | None = Field(default=None, validation_alias=AliasChoices("COMPETESCOPE_SERPER_API_KEY", "SERPER_API_KEY"))
    brave_search_api_key: str | None = Field(default=None, validation_alias=AliasChoices("COMPETESCOPE_BRAVE_SEARCH_API_KEY", "BRAVE_SEARCH_API_KEY"))
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("COMPETESCOPE_LLM_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("COMPETESCOPE_LLM_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL"),
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    max_search_results_per_competitor: int = 3
    max_crawl_documents: int = 24
    crawler_user_agent: str = "CompeteScopeAI/0.1 (+https://example.local/compliance)"
    crawler_rate_limit_seconds: float = 0.6
    crawler_concurrency: int = 4
    crawler_request_timeout_seconds: float = 10.0
    crawler_robots_timeout_seconds: float = 4.0
    crawler_max_html_bytes: int = 1_000_000
    crawler_max_text_chars: int = 12_000
    task_default_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="COMPETESCOPE_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.serper_api_key = first_env("COMPETESCOPE_SERPER_API_KEY", "SERPER_API_KEY") or settings.serper_api_key or None
    settings.brave_search_api_key = first_env("COMPETESCOPE_BRAVE_SEARCH_API_KEY", "BRAVE_SEARCH_API_KEY") or settings.brave_search_api_key or None
    settings.llm_api_key = first_env("COMPETESCOPE_LLM_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY") or settings.llm_api_key or None
    settings.llm_base_url = first_env("COMPETESCOPE_LLM_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL") or settings.llm_base_url or "https://api.openai.com/v1"
    return settings


def should_simulate(_: Settings) -> bool:
    return SIMULATIVE


def first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return None
