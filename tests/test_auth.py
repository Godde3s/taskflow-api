"""Auth flow tests — register, login, refresh rotation, reuse detection."""
import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "ali@example.com", "password": "S3curePass!x", "full_name": "Ali"})
    assert r.status_code == 201
    assert r.json()["email"] == "ali@example.com"
    assert "hashed_password" not in r.json()  # never leak hashes

    r = await client.post("/api/v1/auth/login",
                          data={"username": "ali@example.com", "password": "S3curePass!x"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


@pytest.mark.asyncio
async def test_duplicate_register_conflict(client):
    payload = {"email": "dup@example.com", "password": "S3curePass!x"}
    await client.post("/api/v1/auth/register", json=payload)
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_wrong_password_401(client):
    await client.post("/api/v1/auth/register", json={
        "email": "pw@example.com", "password": "S3curePass!x"})
    r = await client.post("/api/v1/auth/login",
                          data={"username": "pw@example.com", "password": "WrongPass!9"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_short_password_rejected(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "short@example.com", "password": "short"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_detection(client, user_tokens):
    old_refresh = user_tokens["refresh_token"]

    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != old_refresh  # rotated

    # replaying the OLD token must fail (reuse detection)
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401

    # and the whole family is now dead — even the NEW token
    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401
