"""Issue and consume single-use email tokens (password reset, verification)."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_token import EmailToken
from app.models.user import User


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_token(
    db: AsyncSession, user: User, purpose: str, ttl: timedelta
) -> str:
    """Create a token, voiding earlier unused tokens of the same purpose."""
    now = datetime.now(UTC)
    await db.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw = secrets.token_urlsafe(32)
    db.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=_hash(raw),
            expires_at=now + ttl,
        )
    )
    await db.commit()
    return raw


async def consume_token(db: AsyncSession, raw: str, purpose: str) -> User | None:
    """Return the token's user and mark it used, or None if invalid/expired/used."""
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token_hash == _hash(raw), EmailToken.purpose == purpose
        )
    )
    token = result.scalar_one_or_none()
    if token is None or token.used_at is not None:
        return None
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if expires_at <= now:
        return None
    user = await db.get(User, token.user_id)
    if user is None:
        return None
    token.used_at = now
    return user
