"""Serve every /api route under a stable /api/v1 prefix as well.

External clients should call /api/v1/...; the unversioned /api/... paths keep
working for the bundled frontend. A rewrite keeps a single implementation and a
single OpenAPI document, and leaves room for a future /api/v2 with changed contracts.
"""

from starlette.types import ASGIApp, Receive, Scope, Send

_PREFIX = "/api/v1/"


class ApiVersionMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and scope["path"].startswith(_PREFIX):
            rewritten = "/api/" + scope["path"][len(_PREFIX) :]
            scope = dict(scope)
            scope["path"] = rewritten
            if scope.get("raw_path"):
                scope["raw_path"] = rewritten.encode("latin-1")
        await self.app(scope, receive, send)
