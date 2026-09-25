"""pytest fixtures — isolated async app + DB per test."""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.deps import _LOGIN_BUCKETS
from app.main import app
from app.models import User
from app.security import decode_access_token


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestingSession = async_sessionmaker(engine, expire_on_commit=False)
    app.state.testing_session_factory = TestingSession

    async def override_get_db():
        async with TestingSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    _LOGIN_BUCKETS.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def user_tokens(client: AsyncClient) -> dict:
    """Register + login a regular user; returns token pair JSON."""
    await client.post("/api/v1/auth/register", json={
        "email": "reza@example.com", "password": "S3curePass!x", "full_name": "Reza"})
    login = await client.post("/api/v1/auth/login",
                              data={"username": "reza@example.com", "password": "S3curePass!x"})
    return login.json()


@pytest_asyncio.fixture
async def admin_tokens(client: AsyncClient) -> dict:
    """Register a user, elevate to admin directly in DB, login."""
    await client.post("/api/v1/auth/register", json={
        "email": "boss@example.com", "password": "Adm1nPass!x"})
    login = await client.post("/api/v1/auth/login",
                              data={"username": "boss@example.com", "password": "Adm1nPass!x"})
    tokens = login.json()
    user_id = int(decode_access_token(tokens["access_token"]))
    async with app.state.testing_session_factory() as s:
        user = await s.get(User, user_id)
        user.role = "admin"
        await s.commit()
    return tokens
