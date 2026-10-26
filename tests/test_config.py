"""Config guards: a real deployment must never run with the shipped secret."""
import pytest
from pydantic import ValidationError

from app.config import DEV_JWT_SECRET, Settings


def test_local_may_use_the_placeholder():
    s = Settings(environment="local", jwt_secret=DEV_JWT_SECRET)
    assert s.jwt_secret == DEV_JWT_SECRET


def test_production_rejects_the_placeholder():
    with pytest.raises(ValidationError) as exc:
        Settings(environment="production", jwt_secret=DEV_JWT_SECRET)
    assert "JWT_SECRET" in str(exc.value)


def test_production_rejects_short_secrets():
    with pytest.raises(ValidationError):
        Settings(environment="staging", jwt_secret="short-secret")


def test_production_accepts_a_real_secret():
    s = Settings(environment="production", jwt_secret="x" * 40)
    assert len(s.jwt_secret) == 40
