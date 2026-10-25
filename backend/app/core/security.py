"""Security utilities: Argon2 password hashing, JWT tokens, and CSRF protection."""

import contextlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# Initialize Argon2 hasher with secure parameters
_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
)

# Pre-computed dummy hash to defend against timing attacks for non-existent users
_DUMMY_ARGON2_HASH = _password_hasher.hash(
    "animatch_timing_attack_defense_string_dummy"
)

# Common weak passwords list (lowercased)
COMMON_WEAK_PASSWORDS: frozenset[str] = frozenset(
    [
        "1234567890",
        "12345678901",
        "123456789012",
        "password123",
        "password1234",
        "password2024",
        "password2025",
        "password2026",
        "qwertyuiop",
        "qwerty1234",
        "qwerty12345",
        "admin12345",
        "administrator",
        "welcome123",
        "welcome1234",
        "iloveyou123",
        "iloveyou1234",
        "testing123",
        "testing1234",
        "monkey1234",
        "dragon1234",
        "football12",
        "baseball12",
        "basketball1",
        "sunshine12",
        "princess12",
        "master1234",
        "shadow1234",
        "superman12",
        "batman1234",
        "trustno111",
        "letmein123",
        "changeme12",
        "animatch12",
        "animatch123",
        "animatch2026",
    ]
)


def validate_password_strength(password: str) -> None:
    """Validates password length and rejects common weak passwords.

    Raises:
        ValueError: If password is too short, common, or simple.
    """
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters.")

    normalized = password.lower().strip()
    if normalized in COMMON_WEAK_PASSWORDS:
        raise ValueError("Password is too common or easily guessable.")

    # Disallow passwords of all identical characters (e.g. 'aaaaaaaaaa')
    if len(set(password)) <= 1:
        raise ValueError("Password cannot consist of a single repeated character.")


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verifies a plaintext password against an Argon2 hash.

    Employs constant-time dummy verification when hashed_password is None
    to prevent timing attacks that reveal whether an account exists.
    """
    if not hashed_password:
        with contextlib.suppress(VerifyMismatchError):
            _password_hasher.verify(_DUMMY_ARGON2_HASH, plain_password)
        return False

    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Generates a signed HS256 JWT access token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodes and validates a JWT access token. Returns claims dict or None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def generate_csrf_token() -> str:
    """Generates a cryptographically secure random token for CSRF protection."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    """Constant-time double-submit CSRF verification."""
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)
