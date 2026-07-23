from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    database_url: str

    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_market_research_model: str = "gemini-3.1-pro-preview"

    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_s3_region: str | None = None
    s3_bucket_name: str | None = None

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    api_v1_prefix: str = "/api/v1"
    # The ngrok-free.app entries are for mobile testing through ngrok tunnels — the
    # subdomain is random per tunnel restart, so update this when it changes.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3002",
        "https://2bea-116-58-40-146.ngrok-free.app",
    ]

    feedback_loop_interval_hours: int = 6
    feedback_loop_min_applications: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
