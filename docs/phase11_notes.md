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
