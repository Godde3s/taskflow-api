# ⚙️ TaskFlow API

![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest_--passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)

> **A production-grade task-management REST API** — JWT auth with refresh rotation, RBAC, rate limiting, Redis caching, structured logging and a full pytest suite. Built the way a backend should ship in 2026: secure by default, observable, containerized and documented.

**TaskFlow** is the reference backend for my API engineering portfolio. It pairs with [postman-api-testing-toolkit](https://github.com/Godde3s/postman-api-testing-toolkit), whose Postman collection runs against this API.

---

## ✨ Features

### Security first
- **JWT access + refresh tokens** — refresh rotation with reuse detection (a replayed refresh token invalidates the whole family)
- **RBAC** — `admin` / `user` roles enforced via dependency-injected guards
- **Password hashing** — bcrypt with per-user salt via `passlib`
- **Rate limiting** — sliding-window limiter on auth endpoints (Redis-backed)
- **Request IDs** — every response carries `X-Request-ID` for trace correlation
- **CORS + security headers** — explicit allow-list, `no-store` on auth routes

### Engineering quality
- **SQLAlchemy 2.0** async ORM + Alembic migrations
- **Redis caching** on hot reads with cache invalidation on writes
- **Pydantic v2** settings management (12-factor, env-driven)
- **Structured JSON logging** — ready for Loki/ELK ingestion
- **pytest suite** — auth, CRUD, permissions, rate limiting; Testcontainers-free in-memory stack
- **OpenAPI docs** auto-generated at `/docs` (Swagger) and `/redoc`

---

## 🚀 Quickstart

### Docker Compose (recommended)
```bash
git clone https://github.com/Godde3s/taskflow-api.git
cd taskflow-api
cp .env.example .env            # defaults work out of the box
docker compose up --build
# API      → http://localhost:8000/docs
# Postgres → localhost:5432   Redis → localhost:6379
```

### Local (uv or pip)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Run the test suite
```bash
pytest -v --tb=short
```

---

## 🗺️ API surface

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/api/v1/auth/register` | — | Create account (email, password, name) |
| POST | `/api/v1/auth/login` | — | OAuth2 password flow → access + refresh tokens |
| POST | `/api/v1/auth/refresh` | refresh | Rotate refresh token, issue new access token |
| GET | `/api/v1/users/me` | user | Current profile |
| GET | `/api/v1/tasks` | user | List tasks (filter by status, pagination) |
| POST | `/api/v1/tasks` | user | Create task |
| GET | `/api/v1/tasks/{id}` | user | Read task (owner or admin) |
| PATCH | `/api/v1/tasks/{id}` | user | Partial update |
| DELETE | `/api/v1/tasks/{id}` | user | Delete (owner or admin) |
| GET | `/api/v1/admin/stats` | **admin** | Platform statistics |
| GET | `/health` | — | Liveness probe |

Full interactive docs: **`http://localhost:8000/docs`**

---

## 🏗️ Architecture

```
┌──────────┐     ┌───────────────────────────────┐
│  Client  │────▶│  FastAPI (uvicorn, async)     │
└──────────┘     │  ├─ routers/    (HTTP layer)  │
                 │  ├─ deps/       (DI guards)   │
                 │  ├─ auth/       (JWT, RBAC)   │
                 │  └─ services/   (business)    │
                 └───────┬──────────────┬────────┘
                         │              │
                 ┌───────▼──────┐  ┌────▼────────┐
                 │ PostgreSQL   │  │ Redis       │
                 │ (SQLAlchemy) │  │ cache+limits│
                 └──────────────┘  └─────────────┘
```

**Design decisions** (why it looks like this):
- **Routers thin, services fat** — HTTP layer only parses/serializes; business rules live in services and are unit-testable without HTTP.
- **Dependencies as security** — auth/RBAC are FastAPI dependencies, so a forgotten guard is a type-checker-visible pattern, not a code-review hope.
- **Refresh-token family rotation** — the #1 JWT mistake is eternal refresh tokens; rotation + reuse detection caps blast radius of a stolen token.
- **Cache-aside with explicit invalidation** — writes delete keys, reads repopulate; no cache-then-db divergence.

---

## 📁 Project layout

```
taskflow-api/
├── app/
│   ├── main.py          # app factory, middleware, routers
│   ├── config.py        # pydantic-settings (env-driven)
│   ├── database.py      # async engine + session
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic v2 DTOs
│   ├── security.py      # JWT issue/verify, bcrypt, rotation logic
│   ├── deps.py          # auth guards, DB/Redis dependencies
│   └── routers/
│       ├── auth.py      # register / login / refresh
│       ├── tasks.py     # task CRUD
│       ├── users.py     # profile
│       └── admin.py     # admin-only stats
├── tests/               # pytest suite (auth, crud, rbac, rate-limit)
├── alembic/             # migrations
├── Dockerfile           # multi-stage, non-root, slim
├── docker-compose.yml   # api + postgres:16 + redis:7
├── postman/             # matching Postman collection
└── pyproject.toml       # deps + ruff + pytest config
```

---

## 🐳 Production notes

- `Dockerfile` runs as **non-root** user, multi-stage build (builder → slim runtime)
- Health checks wired into compose (`/health` + `depends_on: condition: service_healthy`)
- All secrets via env — see `.env.example`; **never** commit real values (enforced by secret scanning on this repo)
- Horizontal scaling safe: no in-process state (sessions are JWT, cache is Redis, files none)

---

## 🧪 Test coverage

```text
tests/test_auth.py        register, login, wrong password, token refresh + reuse detection
tests/test_tasks.py       CRUD lifecycle, ownership rules, pagination, filters
tests/test_rbac.py        admin endpoints reject users, accept admins
tests/test_rate_limit.py  6th login burst → 429 with Retry-After
```

Run: `pytest -v` — all green, no external services needed (SQLite + fakeredis fallback).

---

## 📄 License

MIT — see [LICENSE](LICENSE).

## 👤 Author

**Reza Bazdar (Godde3s)** — full-stack & API engineer
[GitHub](https://github.com/Godde3s) · [Postman Toolkit](https://github.com/Godde3s/postman-api-testing-toolkit) · [Portfolio](https://godde3s.github.io/OR/)
