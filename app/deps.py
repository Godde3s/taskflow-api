"""FastAPI dependencies — auth guards, pagination, rate limiting."""
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"}) from None
    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive or deleted")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user


# ---------------------------------------------------------------- rate limit
_LOGIN_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


async def rate_limit_login(request: Request) -> None:
    """Sliding-window limiter for auth endpoints (per client IP).

    Single-process implementation; swap `_LOGIN_BUCKETS` for Redis INCR/EXPIRE
    in multi-instance deployments (settings.redis_enabled=True path).
    """
    ip = (request.client.host if request.client else "unknown")
    now = time.monotonic()
    window = 60.0
    bucket = _LOGIN_BUCKETS[ip]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= 6:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many attempts — slow down",
            headers={"Retry-After": str(int(window))},
        )
    bucket.append(now)
