"""Tests for Phase 3 Accounts and Authentication."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import auth_rate_limiter
from app.models.user import User


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Resets rate limiter state before every test."""
    auth_rate_limiter.reset()
    yield
    auth_rate_limiter.reset()


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    """Verifies that a user can register, receives cookies, and password_hash is not exposed."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "valid_secure_password_123",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user1@example.com"
    assert data["display_name"] == "Test User"
    assert data["show_mature"] is False
    assert "password" not in data
    assert "password_hash" not in data

    # Verify cookies
    assert settings.SESSION_COOKIE_NAME in response.cookies
    assert settings.CSRF_COOKIE_NAME in response.cookies

    # Verify in DB
    result = await db_session.execute(
        select(User).where(User.email == "user1@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != "valid_secure_password_123"
    assert user.password_hash.startswith("$argon2")


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client: AsyncClient):
    """Verifies that short, common, and trivial passwords are rejected with 400."""
    # Too short (< 10 chars)
    res_short = await client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert res_short.status_code in (400, 422)

    # Common weak password
    res_weak = await client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "password": "password123"},
    )
    assert res_weak.status_code == 400
    assert "common or easily guessable" in res_weak.json()["detail"].lower()

    # Repeated identical characters
    res_repeat = await client.post(
        "/api/auth/register",
        json={"email": "repeat@example.com", "password": "aaaaaaaaaaaa"},
    )
    assert res_repeat.status_code == 400
    assert "single repeated character" in res_repeat.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client: AsyncClient):
    """Verifies that registering an already registered email fails with 400."""
    reg1 = await client.post(
        "/api/auth/register",
        json={
            "email": "dupe@example.com",
            "password": "password_long_12345",
            "display_name": "First User",
        },
    )
    assert reg1.status_code == 201

    # Second registration with same email (case insensitive)
    reg2 = await client.post(
        "/api/auth/register",
        json={
            "email": "DUPE@example.com",
            "password": "another_long_password_987",
            "display_name": "Second User",
        },
    )
    assert reg2.status_code == 400
    assert "already exists" in reg2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_logout(client: AsyncClient):
    """Verifies login succeeds, returns user data without passwords, and logout clears cookies."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "secure_password_9999",
            "display_name": "Login User",
        },
    )

    # Login
    login_res = await client.post(
        "/api/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "secure_password_9999",
        },
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["email"] == "loginuser@example.com"
    assert "password_hash" not in data
    assert settings.SESSION_COOKIE_NAME in login_res.cookies
    assert settings.CSRF_COOKIE_NAME in login_res.cookies

    csrf_token = login_res.cookies[settings.CSRF_COOKIE_NAME]

    # Logout (requires CSRF)
    logout_res = await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_login_wrong_password_and_generic_error(client: AsyncClient):
    """Verifies that wrong password and non-existent email return generic 401."""
    # Register user
    await client.post(
        "/api/auth/register",
        json={
            "email": "existing@example.com",
            "password": "my_correct_password_123",
        },
    )

    # Wrong password for existing user
    res_wrong = await client.post(
        "/api/auth/login",
        json={
            "email": "existing@example.com",
            "password": "wrong_password_321",
        },
    )
    assert res_wrong.status_code == 401
    assert res_wrong.json()["detail"] == "Invalid email or password"

    # Non-existent email
    res_nonexistent = await client.post(
        "/api/auth/login",
        json={
            "email": "ghost@example.com",
            "password": "wrong_password_321",
        },
    )
    assert res_nonexistent.status_code == 401
    assert res_nonexistent.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_rate_limiting_lockout(client: AsyncClient):
    """Verifies that repeated failed attempts trigger 429 Too Many Requests with Retry-After."""
    # Attempt 5 failed logins for an email
    for _ in range(5):
        res = await client.post(
            "/api/auth/login",
            json={"email": "target@example.com", "password": "wrong_password_abc"},
        )
        assert res.status_code == 401

    # 6th attempt should be blocked by rate limiter
    blocked_res = await client.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "wrong_password_abc"},
    )
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers
    assert "too many failed attempts" in blocked_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_csrf_rejection_and_acceptance(client: AsyncClient):
    """Verifies that state-changing authenticated requests reject invalid/missing CSRF."""
    # Register and get session
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "csrf_test@example.com",
            "password": "secure_csrf_password_1",
        },
    )
    assert reg.status_code == 201
    valid_csrf = reg.cookies[settings.CSRF_COOKIE_NAME]

    # 1. State change without X-CSRF-Token header -> 403 Forbidden
    res_no_header = await client.patch(
        "/api/auth/me",
        json={"display_name": "Hacked Name"},
    )
    assert res_no_header.status_code == 403
    assert "CSRF token validation failed" in res_no_header.json()["detail"]

    # 2. State change with mismatched X-CSRF-Token header -> 403 Forbidden
    res_mismatch = await client.patch(
        "/api/auth/me",
        headers={"X-CSRF-Token": "invalid_forged_token"},
        json={"display_name": "Hacked Name"},
    )
    assert res_mismatch.status_code == 403

    # 3. State change with correct X-CSRF-Token header -> 200 OK
    res_valid = await client.patch(
        "/api/auth/me",
        headers={"X-CSRF-Token": valid_csrf},
        json={"display_name": "Updated Valid Name", "show_mature": True},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["display_name"] == "Updated Valid Name"
    assert res_valid.json()["show_mature"] is True


@pytest.mark.asyncio
async def test_get_me_unauthorized_and_authorized(client: AsyncClient):
    """Verifies GET /api/auth/me returns 401 without session and user profile with session."""
    # Without session
    res_unauth = await client.get("/api/auth/me")
    assert res_unauth.status_code == 401

    # Register and automatically set session
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "me_user@example.com",
            "password": "secure_password_profile_1",
            "display_name": "Profile User",
        },
    )
    assert reg.status_code == 201

    # With session
    res_auth = await client.get("/api/auth/me")
    assert res_auth.status_code == 200
    assert res_auth.json()["email"] == "me_user@example.com"
    assert res_auth.json()["display_name"] == "Profile User"


@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient, db_session: AsyncSession):
    """Verifies that DELETE /api/auth/me deletes the account and all related data."""
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "delete_me@example.com",
            "password": "secure_password_to_delete_1",
        },
    )
    assert reg.status_code == 201
    csrf_token = reg.cookies[settings.CSRF_COOKIE_NAME]

    # Delete account
    del_res = await client.delete(
        "/api/auth/me",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Account deleted successfully"

    # Verify user is gone from DB
    result = await db_session.execute(
        select(User).where(User.email == "delete_me@example.com")
    )
    assert result.scalar_one_or_none() is None

    # Verify subsequent GET /api/auth/me is unauthorized
    me_res = await client.get("/api/auth/me")
    assert me_res.status_code == 401


@pytest.mark.asyncio
async def test_google_oauth_not_configured(client: AsyncClient):
    """Verifies /api/auth/google/login returns 400 when Google credentials are not set."""
    with patch("app.services.oauth.is_google_oauth_configured", return_value=False):
        res = await client.get("/api/auth/google/login")
        assert res.status_code == 400
        assert "not configured" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_oauth_callback_creates_new_user(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that a verified Google callback registers a new user."""
    mock_user_info = {
        "sub": "google-sub-1001",
        "email": "newgoogle@example.com",
        "email_verified": True,
        "name": "New Google User",
    }

    with (
        patch("app.api.auth.is_google_oauth_configured", return_value=True),
        patch("app.services.oauth.is_google_oauth_configured", return_value=True),
        patch(
            "app.services.oauth.GoogleOAuthService.extract_user_info",
            new_callable=AsyncMock,
            return_value=mock_user_info,
        ),
    ):
        res = await client.get(
            "/api/auth/google/callback",
            headers={"Accept": "application/json"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "newgoogle@example.com"
        assert data["display_name"] == "New Google User"
        assert settings.SESSION_COOKIE_NAME in res.cookies

        # Verify in DB
        result = await db_session.execute(
            select(User).where(User.google_sub == "google-sub-1001")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.password_hash is None


@pytest.mark.asyncio
async def test_google_oauth_callback_refuses_auto_link_for_password_account(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that Google callback refuses to auto-link to an existing email/password account."""
    # First create an email/password account
    await client.post(
        "/api/auth/register",
        json={
            "email": "refuseme@example.com",
            "password": "existing_local_password_1",
            "display_name": "Refuse Me Local",
        },
    )
    # Clear session cookies to simulate unauthenticated Google login flow
    client.cookies.clear()

    mock_user_info = {
        "sub": "google-sub-refused-111",
        "email": "refuseme@example.com",
        "email_verified": True,
        "name": "Refuse Me Google",
    }

    with (
        patch("app.api.auth.is_google_oauth_configured", return_value=True),
        patch("app.services.oauth.is_google_oauth_configured", return_value=True),
        patch(
            "app.services.oauth.GoogleOAuthService.extract_user_info",
            new_callable=AsyncMock,
            return_value=mock_user_info,
        ),
    ):
        res = await client.get(
            "/api/auth/google/callback",
            headers={"Accept": "application/json"},
        )
        assert res.status_code == 400
        assert (
            "Please sign in with your password and connect Google from Settings"
            in res.json()["detail"]
        )

        # Verify user was NOT linked
        result = await db_session.execute(
            select(User).where(User.email == "refuseme@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.google_sub is None


@pytest.mark.asyncio
async def test_google_link_logged_in_endpoint(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that a logged-in user can link their Google account from Settings."""
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "loggedin_link@example.com",
            "password": "my_password_for_linking_1",
            "display_name": "Link User",
        },
    )
    assert reg.status_code == 201
    csrf_token = reg.cookies[settings.CSRF_COOKIE_NAME]

    mock_user_info = {
        "sub": "google-sub-linked-success-999",
        "email": "loggedin_link@example.com",
        "email_verified": True,
        "name": "Link User Google",
    }

    with (
        patch("app.api.auth.is_google_oauth_configured", return_value=True),
        patch("app.services.oauth.is_google_oauth_configured", return_value=True),
        patch(
            "app.services.oauth.GoogleOAuthService.verify_id_token",
            new_callable=AsyncMock,
            return_value=mock_user_info,
        ),
    ):
        link_res = await client.post(
            "/api/auth/google/link",
            headers={"X-CSRF-Token": csrf_token},
            json={"id_token": "valid_google_mock_id_token"},
        )
        assert link_res.status_code == 200

        # Verify in DB
        result = await db_session.execute(
            select(User).where(User.email == "loggedin_link@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.google_sub == "google-sub-linked-success-999"


@pytest.mark.asyncio
async def test_google_link_refuses_conflict_with_another_account(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that linking fails if the Google account is already linked to another user."""
    # Create user A already linked to google-sub-conflict
    user_a = User(
        email="usera@example.com",
        password_hash=None,
        google_sub="google-sub-conflict",
        display_name="User A",
        show_mature=False,
    )
    db_session.add(user_a)
    await db_session.commit()

    # User B registers with email/password
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "userb@example.com",
            "password": "userb_password_12345",
            "display_name": "User B",
        },
    )
    csrf_token = reg.cookies[settings.CSRF_COOKIE_NAME]

    mock_user_info = {
        "sub": "google-sub-conflict",
        "email": "usera@example.com",
        "email_verified": True,
        "name": "User A",
    }

    with (
        patch("app.api.auth.is_google_oauth_configured", return_value=True),
        patch("app.services.oauth.is_google_oauth_configured", return_value=True),
        patch(
            "app.services.oauth.GoogleOAuthService.verify_id_token",
            new_callable=AsyncMock,
            return_value=mock_user_info,
        ),
    ):
        link_res = await client.post(
            "/api/auth/google/link",
            headers={"X-CSRF-Token": csrf_token},
            json={"id_token": "token_for_user_a_google"},
        )
        assert link_res.status_code == 400
        assert "already linked to another user" in link_res.json()["detail"]


@pytest.mark.asyncio
async def test_password_over_128_characters_rejected(client: AsyncClient):
    """Verifies that passwords longer than 128 characters are rejected."""
    long_password = "a" * 129
    res = await client.post(
        "/api/auth/register",
        json={
            "email": "toolong@example.com",
            "password": long_password,
        },
    )
    assert res.status_code in (400, 422)


@pytest.mark.asyncio
async def test_register_rate_limiting(client: AsyncClient):
    """Verifies that repeated failed registration attempts trigger rate limiting."""
    # Trigger 5 failed register attempts for the same email
    for _ in range(5):
        res = await client.post(
            "/api/auth/register",
            json={"email": "ratelimit_reg@example.com", "password": "password123"},
        )
        assert res.status_code == 400

    # 6th attempt should be blocked with 429
    blocked = await client.post(
        "/api/auth/register",
        json={
            "email": "ratelimit_reg@example.com",
            "password": "valid_password_10chars",
        },
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


@pytest.mark.asyncio
async def test_valid_token_for_deleted_account_returns_401(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that a valid, signed JWT for a deleted user returns 401 Unauthorized."""
    # Register user
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "will_delete@example.com",
            "password": "my_delete_password_123",
            "display_name": "Will Delete",
        },
    )
    assert reg.status_code == 201

    # Delete the user directly in database
    result = await db_session.execute(
        select(User).where(User.email == "will_delete@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    await db_session.delete(user)
    await db_session.commit()

    # Client still has session cookie, but user record is gone
    res = await client.get("/api/auth/me")
    assert res.status_code == 401
    assert "User not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_display_name_trimming(client: AsyncClient):
    """Verifies that display_name is trimmed and whitespace-only defaults to email prefix."""
    res_trimmed = await client.post(
        "/api/auth/register",
        json={
            "email": "trimmed@example.com",
            "password": "valid_secure_pass_123",
            "display_name": "   Spaced Name   ",
        },
    )
    assert res_trimmed.status_code == 201
    assert res_trimmed.json()["display_name"] == "Spaced Name"

    res_empty_name = await client.post(
        "/api/auth/register",
        json={
            "email": "blankname@example.com",
            "password": "valid_secure_pass_123",
            "display_name": "     ",
        },
    )
    assert res_empty_name.status_code == 201
    # Defaults to username from email
    assert res_empty_name.json()["display_name"] == "blankname"


def test_production_jwt_secret_validation():
    """Verifies that production mode fails startup if JWT secret is missing, default, or short."""
    from pydantic import ValidationError

    from app.core.config import Settings

    # Default placeholder fails
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="change-this-in-production-to-a-secure-random-secret-key-at-least-32-chars",
        )

    # Shorter than 32 characters fails
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="too-short-secret-key",
        )

    # Valid >= 32 char secret succeeds
    valid_settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a" * 32,
    )
    assert valid_settings.JWT_SECRET_KEY == "a" * 32


@pytest.mark.asyncio
async def test_google_oauth_callback_rejects_unverified_email(client: AsyncClient):
    """Verifies that an unverified Google email is rejected and never linked."""
    mock_unverified = {
        "sub": "google-sub-unverified",
        "email": "unverified@example.com",
        "email_verified": False,
        "name": "Unverified User",
    }

    with (
        patch("app.api.auth.is_google_oauth_configured", return_value=True),
        patch("app.services.oauth.is_google_oauth_configured", return_value=True),
        patch(
            "app.services.oauth.GoogleOAuthService.extract_user_info",
            new_callable=AsyncMock,
            return_value=mock_unverified,
        ),
    ):
        res = await client.get(
            "/api/auth/google/callback",
            headers={"Accept": "application/json"},
        )
        assert res.status_code == 400
        assert "not verified" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cookie_flags_in_production(client: AsyncClient):
    """Verifies cookie flags (httpOnly, SameSite=Lax, Secure in production)."""
    with patch.object(settings, "ENVIRONMENT", "production"):
        res = await client.post(
            "/api/auth/register",
            json={
                "email": "prod_flags@example.com",
                "password": "secure_production_password_1",
            },
        )
        assert res.status_code == 201

        # Check Set-Cookie headers
        set_cookies = res.headers.get_list("set-cookie")
        access_cookie_header = next(
            (c for c in set_cookies if settings.SESSION_COOKIE_NAME in c), None
        )
        assert access_cookie_header is not None
        assert "httponly" in access_cookie_header.lower()
        assert "samesite=lax" in access_cookie_header.lower()
        assert "secure" in access_cookie_header.lower()


@pytest.mark.asyncio
async def test_get_auth_providers(client: AsyncClient):
    """GET /api/auth/providers returns configured status for OAuth providers."""
    res = await client.get("/api/auth/providers")
    assert res.status_code == 200
    data = res.json()
    assert "google" in data
    assert isinstance(data["google"], bool)

