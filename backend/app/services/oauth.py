"""Google OAuth service using Authlib."""

from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from starlette.requests import Request

from app.core.config import settings

oauth = OAuth()


def is_google_oauth_configured() -> bool:
    """Returns True if Google OAuth credentials are configured."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


if is_google_oauth_configured():
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


class GoogleOAuthService:
    """Service to handle Google OAuth login and callback processing."""

    @classmethod
    def get_client(cls):
        """Returns the registered Google OAuth client or raises 400 if not configured."""
        if not is_google_oauth_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google OAuth is not configured",
            )
        client = getattr(oauth, "google", None)
        if not client:
            oauth.register(
                name="google",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
            client = oauth.google
        return client

    @classmethod
    async def extract_user_info(cls, request: Request) -> dict[str, Any]:
        """Exchanges authorization code for tokens and extracts verified userinfo.

        Returns:
            dict containing 'sub', 'email', 'email_verified', and 'name'.
        """
        client = cls.get_client()
        token = await client.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            # Fallback to parse_id_token if userinfo is not directly nested
            user_info = await client.parse_id_token(request, token)

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not retrieve user information from Google",
            )

        return {
            "sub": str(user_info.get("sub")),
            "email": user_info.get("email", "").lower().strip(),
            "email_verified": bool(user_info.get("email_verified", False)),
            "name": user_info.get("name") or user_info.get("email", "").split("@")[0],
        }

    @classmethod
    async def verify_id_token(cls, id_token: str) -> dict[str, Any]:
        """Validates a Google ID token and returns verified identity claims."""
        client = cls.get_client()
        token = {"id_token": id_token}
        user_info = await client.parse_id_token(token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not verify Google ID token",
            )
        return {
            "sub": str(user_info.get("sub")),
            "email": user_info.get("email", "").lower().strip(),
            "email_verified": bool(user_info.get("email_verified", False)),
            "name": user_info.get("name") or user_info.get("email", "").split("@")[0],
        }
