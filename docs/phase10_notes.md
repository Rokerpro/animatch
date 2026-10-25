# Phase 10: Hardening, Security Auditing, and Deployment Notes

## Reverse Proxy Client IP & Rate Limiting Requirements

> [!IMPORTANT]
> **Reverse Proxy Real Client IP Detection**:
> In local development, client IP is extracted directly from the incoming connection (`request.client.host`).
> In production deployments (Phase 10) behind a reverse proxy (e.g. Nginx, Caddy, Cloudflare, or AWS ALB):
> 1. Per-IP rate limiting on `/api/auth/login` and `/api/auth/register` must extract the real client IP only from trusted reverse proxy headers.
> 2. Direct client manipulation of `X-Forwarded-For` must be ignored or stripped at the ingress proxy.
> 3. Uvicorn/FastAPI must be configured with `--forwarded-allow-ips` (or a trusted proxy middleware) restricted to known internal proxy IP ranges (e.g., `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`) so an external attacker cannot forge `X-Forwarded-For` headers to bypass sliding-window rate limits or trigger denial-of-service on arbitrary IP addresses.
