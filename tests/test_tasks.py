"""Task CRUD + ownership + RBAC tests."""
import pytest

AUTH = "Authorization"


def bearer(tokens):
    return {AUTH: f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_task_crud_lifecycle(client, user_tokens):
    h = bearer(user_tokens)
    r = await client.post("/api/v1/tasks", headers=h,
                          json={"title": "Write security report", "priority": 1})
    assert r.status_code == 201
    task = r.json()
    assert task["status"] == "todo" and task["priority"] == 1

    r = await client.get(f"/api/v1/tasks/{task['id']}", headers=h)
    assert r.status_code == 200

    r = await client.patch(f"/api/v1/tasks/{task['id']}", headers=h,
                           json={"status": "done"})
    assert r.json()["status"] == "done"

    r = await client.delete(f"/api/v1/tasks/{task['id']}", headers=h)
    assert r.status_code == 204
    assert (await client.get(f"/api/v1/tasks/{task['id']}", headers=h)).status_code == 404


@pytest.mark.asyncio
async def test_tasks_require_auth(client):
    r = await client.get("/api/v1/tasks")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ownership_enforced(client, user_tokens):
    """User B must not touch user A's task."""
    a = user_tokens
    await client.post("/api/v1/auth/register", json={
        "email": "other@example.com", "password": "OtherPass!1"})
    b = (await client.post("/api/v1/auth/login",
                           data={"username": "other@example.com", "password": "OtherPass!1"})).json()

    task = (await client.post("/api/v1/tasks", headers=bearer(a),
                              json={"title": "A's private task"})).json()

    r = await client.get(f"/api/v1/tasks/{task['id']}", headers=bearer(b))
    assert r.status_code == 403

    r = await client.delete(f"/api/v1/tasks/{task['id']}", headers=bearer(b))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_any_task(client, user_tokens, admin_tokens):
    task = (await client.post("/api/v1/tasks", headers=bearer(user_tokens),
                              json={"title": "user task"})).json()
    r = await client.get(f"/api/v1/tasks/{task['id']}", headers=bearer(admin_tokens))
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_stats_rbac(client, user_tokens, admin_tokens):
    assert (await client.get("/api/v1/admin/stats", headers=bearer(user_tokens))).status_code == 403
    r = await client.get("/api/v1/admin/stats", headers=bearer(admin_tokens))
    assert r.status_code == 200
    assert {"users", "tasks", "tasks_done"} <= set(r.json())


@pytest.mark.asyncio
async def test_pagination_and_filters(client, user_tokens):
    h = bearer(user_tokens)
    for i in range(7):
        await client.post("/api/v1/tasks", headers=h, json={"title": f"t{i}"})
    page1 = (await client.get("/api/v1/tasks", headers=h, params={"page": 1, "size": 5})).json()
    assert page1["total"] == 7 and len(page1["items"]) == 5
    page2 = (await client.get("/api/v1/tasks", headers=h, params={"page": 2, "size": 5})).json()
    assert len(page2["items"]) == 2
    done = (await client.get("/api/v1/tasks", headers=h, params={"task_status": "done"})).json()
    assert done["total"] == 0


@pytest.mark.asyncio
async def test_rate_limit_on_login_burst(client):
    await client.post("/api/v1/auth/register", json={
        "email": "rl@example.com", "password": "S3curePass!x"})
    codes = []
    for _ in range(7):
        r = await client.post("/api/v1/auth/login",
                              data={"username": "rl@example.com", "password": "S3curePass!x"})
        codes.append(r.status_code)
    assert 429 in codes  # burst exceeded → rate limited
    assert codes.count(200) >= 1  # legit login still succeeded initially
