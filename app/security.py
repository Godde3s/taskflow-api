"""JWT issuing/verification, bcrypt hashing, refresh-token rotation.

Security properties implemented here:
- Short-lived access tokens (15 min) + rotating refresh tokens (7 days)
- Refresh-token family rotation with REUSE DETECTION: using an already-used
  refresh token invalidates the entire family (bearer of a stolen token gets
  logged out together with the legitimate user).
- bcrypt password hashing (cost 12).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# In a multi-instance deployment this lives in Redis; a dict keeps the demo
# single-process friendly while showing the exact rotation semantics.
_REFRESH_FAMILIES: dict[str, set[str]] = {}  # family_id -> live jti set
_JTI_TO_FAMILY: dict[str, str] = {}          # live jti -> family_id
_RETIRED_JTI: dict[str, str] = {}            # used jti -> family_id (for reuse detection)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if token_type == "refresh":
        import uuid

        jti = uuid.uuid4().hex
        payload["jti"] = jti
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), payload.get("jti")


def create_access_token(user_id: int | str) -> str:
    token, _ = _create_token(str(user_id), timedelta(minutes=settings.access_token_ttl_minutes), "access")
    return token


def _kill_family(family_id: str) -> None:
    """Revoke every live token of a family (stolen-token blast-radius cap)."""
    for jti in _REFRESH_FAMILIES.pop(family_id, set()):
        _JTI_TO_FAMILY.pop(jti, None)


def create_refresh_family(user_id: int | str) -> str:
    """Start a new refresh family and return the first refresh token."""
    import uuid

    family_id = uuid.uuid4().hex
    token, jti = _create_token(str(user_id), timedelta(days=settings.refresh_token_ttl_days), "refresh")
    _REFRESH_FAMILIES[family_id] = {jti}
    _JTI_TO_FAMILY[jti] = family_id
    return token


def rotate_refresh_token(token: str) -> tuple[str, str]:
    """Validate + rotate. Returns (new_refresh, user_id).

    Raises jwt exceptions on tampering/expiry and ValueError on reuse.
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "refresh":
        raise ValueError("not a refresh token")
    jti = payload.get("jti", "")
    family_id = _JTI_TO_FAMILY.get(jti)
    if family_id is None:
        # Reuse of an already-rotated token → treat as theft:
        # revoke the WHOLE family (including the token the attacker holds).
        stolen_family = _RETIRED_JTI.get(jti)
        if stolen_family:
            _kill_family(stolen_family)
        raise ValueError("refresh token reuse detected — family revoked")
    _REFRESH_FAMILIES[family_id].discard(jti)
    _JTI_TO_FAMILY.pop(jti, None)
    _RETIRED_JTI[jti] = family_id  # remember so replay triggers family kill
    new_token, new_jti = _create_token(payload["sub"], timedelta(days=settings.refresh_token_ttl_days), "refresh")
    _REFRESH_FAMILIES[family_id].add(new_jti)
    _JTI_TO_FAMILY[new_jti] = family_id
    return new_token, payload["sub"]


def decode_access_token(token: str) -> str:
    """Returns the subject (user id) for a valid *access* token."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise ValueError("not an access token")
    return payload["sub"]
