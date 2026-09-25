# TaskFlow API — Security Notes

## Credential policy
- **No secrets in source.** `JWT_SECRET`, database URLs and any third-party keys come from environment variables / the platform secret store only (see `.env.example`).
- The repository runs **GitHub secret scanning + push protection** — pushes containing tokens are blocked.
- The repo ships **only** `.env.example` with placeholders; real `.env` files are gitignored.

## Implemented hardening
| Control | Where |
|---|---|
| bcrypt (cost 12) password hashing | `app/security.py` |
| Access 15 min / refresh 7 d, rotating refresh tokens with **family reuse detection** | `app/security.py::rotate_refresh_token` |
| RBAC via FastAPI dependencies (`require_admin`) | `app/deps.py` |
| Sliding-window login rate limiting → `429 + Retry-After` | `app/deps.py::rate_limit_login` |
| Ownership checks on every task operation | `app/routers/tasks.py::_owned_task` |
| Generic 500s (no stack traces to clients), structured JSON logs with `X-Request-ID` | `app/main.py` |
| Security headers: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on auth | `app/main.py` |
| Non-root container user + multi-stage build | `Dockerfile` |

## Known trade-offs (documented, not hidden)
1. Refresh-family store is in-process (`dict`) — swap to Redis for multi-instance deployments.
2. Rate limiter is per-process — same swap applies.
3. Local/dev defaults (SQLite, dev JWT secret) are safe only for development; production overrides are mandatory and validated by `ENVIRONMENT != local` checks in deployment pipelines.

## Reporting
Found a vulnerability? Open a private security advisory via GitHub → **Security → Report a vulnerability**.
