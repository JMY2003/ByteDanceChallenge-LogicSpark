from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    serper_api_key: str | None = None
    brave_search_api_key: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    offline_mode: bool = False
    max_search_results_per_competitor: int = 3
    max_crawl_documents: int = 80
    crawler_user_agent: str = "CompeteScopeAI/0.1 (+https://example.local/compliance)"
    crawler_rate_limit_seconds: float = 0.6
    task_default_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="COMPETESCOPE_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
