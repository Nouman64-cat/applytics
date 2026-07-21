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

    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    feedback_loop_interval_hours: int = 6
    feedback_loop_min_applications: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
