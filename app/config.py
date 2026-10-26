"""Pydantic v2 settings — 12-factor, environment-driven.

Every value has a safe local default; production overrides come from env
vars or the platform secret store. No secrets are ever hardcoded here.
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The placeholder used by local runs. It is public knowledge (it ships in this
# repository), so any deployment that keeps it hands out free JWT forgery.
DEV_JWT_SECRET = "dev-only-secret-change-me-in-production"
LOCAL_ENVIRONMENTS = {"local", "dev", "development", "test", "testing"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- app ---
    app_name: str = "TaskFlow API"
    environment: str = "local"          # local | staging | production
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- security ---
    # DEV-ONLY default; production MUST set JWT_SECRET via env/secret store.
    jwt_secret: str = DEV_JWT_SECRET
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

    @model_validator(mode="after")
    def _reject_placeholder_secret_outside_local(self) -> "Settings":
        """Refuse to boot a real deployment with the shipped placeholder secret.

        A default that is checked into git makes every signature check
        worthless: anyone can mint an admin token. Fail fast instead of
        starting in a state that looks healthy but is trivially bypassed.
        """
        if self.environment.strip().lower() in LOCAL_ENVIRONMENTS:
            return self
        if self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET is still the built-in development placeholder. "
                "Set a unique secret (>= 32 chars) before running with "
                f"ENVIRONMENT={self.environment!r}."
            )
        if len(self.jwt_secret) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters outside local "
                f"development (ENVIRONMENT={self.environment!r})."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
