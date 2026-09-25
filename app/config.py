"""Pydantic v2 settings — 12-factor, environment-driven.

Every value has a safe local default; production overrides come from env
vars or the platform secret store. No secrets are ever hardcoded here.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- app ---
    app_name: str = "TaskFlow API"
    environment: str = "local"          # local | staging | production
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- security ---
    # DEV-ONLY default; production MUST set JWT_SECRET via env/secret store.
    jwt_secret: str = "dev-only-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # --- rate limiting (auth endpoints) ---
    rate_limit_attempts: int = 5
    rate_limit_window_seconds: int = 60

    # --- database ---
    database_url: str = "sqlite+aiosqlite:///./taskflow.db"  # prod: postgresql+asyncpg://…

    # --- redis ---
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False          # tests / bare local runs disable it

    # --- cors ---
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
