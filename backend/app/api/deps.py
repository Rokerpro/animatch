"""Reusable authentication and security dependencies."""

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token, verify_csrf_token
from app.db.session import get_db
from app.models.user import User


def get_token_from_request(
    request: Request,
    access_token_cookie: str | None = None,
    authorization_header: str | None = None,
) -> str | None:
    """Extracts access token from httpOnly cookie or Authorization Bearer header."""
    if access_token_cookie:
        return access_token_cookie
    auth = authorization_header or request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[len("Bearer ") :].strip()
    return request.cookies.get(settings.SESSION_COOKIE_NAME)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[
        str | None, Cookie(alias=settings.SESSION_COOKIE_NAME)
    ] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Reusable dependency that requires an authenticated user.

    Raises:
        HTTPException: 401 Unauthorized if token is missing, expired, or user not found.
    """
    token = get_token_from_request(request, access_token, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[
        str | None, Cookie(alias=settings.SESSION_COOKIE_NAME)
    ] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Reusable dependency that returns the authenticated User or None if unauthenticated."""
    token = get_token_from_request(request, access_token, authorization)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def verify_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Validates double-submit CSRF token on state-changing requests.

    Compares the value in the X-CSRF-Token header with the csrf_token cookie.
    Raises:
        HTTPException: 403 Forbidden if tokens are missing or mismatch.
    """
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = x_csrf_token or request.headers.get("X-CSRF-Token")

    if not verify_csrf_token(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed. Ensure X-CSRF-Token header matches csrf_token cookie.",
        )
