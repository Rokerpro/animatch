# Phase 11: Hardening, Security Auditing, and Deployment Notes

## Reverse Proxy Client IP & Rate Limiting Requirements

> [!IMPORTANT]
> **Reverse Proxy Real Client IP Detection**:
> In local development, client IP is extracted directly from the incoming connection (`request.client.host`).
> In production deployments (Phase 11) behind a reverse proxy (e.g. Nginx, Caddy, Cloudflare, or AWS ALB):
> 1. Per-IP rate limiting on `/api/auth/login` and `/api/auth/register` must extract the real client IP only from trusted reverse proxy headers.
> 2. Direct client manipulation of `X-Forwarded-For` must be ignored or stripped at the ingress proxy.
> 3. Uvicorn/FastAPI must be configured with `--forwarded-allow-ips` (or a trusted proxy middleware) restricted to known internal proxy IP ranges (e.g., `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`) so an external attacker cannot forge `X-Forwarded-For` headers to bypass sliding-window rate limits or trigger denial-of-service on arbitrary IP addresses.

## Implemented: trusted-proxy client IP

`app/core/client_ip.py` resolves the client IP for auth rate limiting.
`X-Forwarded-For` is honored only when the direct peer matches
`TRUSTED_PROXIES` (IPs or CIDRs, empty by default, so the header is ignored).
The chain is read right to left and the first address outside the trusted set is
the client, so entries a caller prepends cannot spoof an IP. The compose file
trusts the Docker bridge range (`172.16.0.0/12`) for the nginx container.

## Implemented: CI, deployment, and hardening

- `.github/workflows/ci.yml` runs ruff, black, pytest, eslint, prettier, tsc,
  vitest, and the frontend build on pushes to `main` and on pull requests.
- `docker-compose.prod.yml` runs Postgres (`asyncpg`), the backend in
  `ENVIRONMENT=production`, and the nginx frontend, with secrets from the
  environment and no source bind mounts. Run `alembic upgrade head` once after
  the first start, then sync the catalog with `python -m app.cli sync-catalog`.
- The backend image runs as a non-root user and has a `/api/health` healthcheck.
- nginx sends `nosniff`, `X-Frame-Options`, `Referrer-Policy`, and a CSP, and
  hides its version.
- CSRF audit: every state-changing route with a session requires the CSRF
  token. `register` and `login` have no session yet and are rate limited.
  `POST /api/recs/quiz` now requires the token when the caller is signed in,
  because it saves the taste profile.

## Still open

- Choose a host, TLS termination (Caddy or a cloud load balancer), and a domain.
- Database backups and monitoring or error alerting.
- The in-memory rate limiter is per process; use a shared store if the backend
  runs with more than one worker or replica.

## Operations

- **Catalog refresh:** schedule an incremental sync with the host's cron (or a
  scheduled container), for example weekly:
  `docker compose -f docker-compose.prod.yml exec -T backend python -m app.cli sync-catalog --since "$(date -d '7 days ago' +%s)"`
  (`--since` takes an epoch or an ISO date). With
  `INDEX_REFRESH_MINUTES` above 0 the API polls a catalog fingerprint and
  rebuilds the in-memory recommendation index after a sync, so no restart is needed.
- **Request IDs:** every response carries `X-Request-ID` and every log line
  includes it. A well-formed incoming ID is reused so proxies can correlate.
- **Error reporting:** set `SENTRY_DSN` to enable Sentry; personal data is not sent.
- **Email:** set `EMAIL_BACKEND=smtp` with `SMTP_*` and `EMAIL_FROM` for password
  reset and verification mail. The links point at `FRONTEND_URL/reset-password`
  and `FRONTEND_URL/verify-email`; those frontend pages still need to be built.
