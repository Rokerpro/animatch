"""Tests for password reset and email verification."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import auth_rate_limiter
from app.models.email_token import EmailToken
from app.models.user import User
from app.services.email import LogEmailSender, SmtpEmailSender, get_email_sender

PASSWORD = "secure_password_12345"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    auth_rate_limiter.reset()
    yield
    auth_rate_limiter.reset()


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    sent: list[tuple[str, str, str]] = []

    async def fake_send(to: str, subject: str, body: str) -> None:
        sent.append((to, subject, body))

    monkeypatch.setattr("app.api.auth.send_email_safely", fake_send)
    return sent


def token_from(message: tuple[str, str, str]) -> str:
    match = re.search(r"token=([\w-]+)", message[2])
    assert match
    return match.group(1)


async def register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 201
    return response.cookies["csrf_token"]


@pytest.mark.asyncio
async def test_register_sends_verification_and_verify_marks_user(
    client: AsyncClient, outbox: list, db_session: AsyncSession
):
    await register(client, "verify@example.com")
    assert len(outbox) == 1 and outbox[0][0] == "verify@example.com"

    response = await client.post(
        "/api/auth/verify-email", json={"token": token_from(outbox[0])}
    )
    assert response.status_code == 200
    user = (await db_session.execute(select(User))).scalar_one()
    await db_session.refresh(user)
    assert user.email_verified_at is not None


@pytest.mark.asyncio
async def test_verification_token_is_single_use(client: AsyncClient, outbox: list):
    await register(client, "once@example.com")
    token = token_from(outbox[0])
    assert (
        await client.post("/api/auth/verify-email", json={"token": token})
    ).status_code == 200
    assert (
        await client.post("/api/auth/verify-email", json={"token": token})
    ).status_code == 400


@pytest.mark.asyncio
async def test_resend_verification_requires_csrf_and_skips_verified(
    client: AsyncClient, outbox: list
):
    csrf = await register(client, "resend@example.com")
    assert (await client.post("/api/auth/resend-verification")).status_code == 403

    response = await client.post(
        "/api/auth/resend-verification", headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert len(outbox) == 2

    await client.post("/api/auth/verify-email", json={"token": token_from(outbox[1])})
    again = await client.post(
        "/api/auth/resend-verification", headers={"X-CSRF-Token": csrf}
    )
    assert again.json()["message"] == "Email already verified."
    assert len(outbox) == 2


@pytest.mark.asyncio
async def test_forgot_password_is_generic_for_unknown_email(
    client: AsyncClient, outbox: list
):
    response = await client.post(
        "/api/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    assert outbox == []


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient, outbox: list):
    await register(client, "reset@example.com")
    outbox.clear()
    await client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert len(outbox) == 1
    token = token_from(outbox[0])

    weak = await client.post(
        "/api/auth/reset-password", json={"token": token, "password": "short"}
    )
    assert weak.status_code in (400, 422)

    new_password = "brand_new_password_987"
    ok = await client.post(
        "/api/auth/reset-password", json={"token": token, "password": new_password}
    )
    assert ok.status_code == 200

    reused = await client.post(
        "/api/auth/reset-password", json={"token": token, "password": new_password}
    )
    assert reused.status_code == 400

    old_login = await client.post(
        "/api/auth/login", json={"email": "reset@example.com", "password": PASSWORD}
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": new_password},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_new_reset_request_voids_previous_token(
    client: AsyncClient, outbox: list
):
    await register(client, "void@example.com")
    outbox.clear()
    await client.post("/api/auth/forgot-password", json={"email": "void@example.com"})
    await client.post("/api/auth/forgot-password", json={"email": "void@example.com"})
    first, second = token_from(outbox[0]), token_from(outbox[1])
    payload = {"password": "brand_new_password_987"}
    assert (
        await client.post("/api/auth/reset-password", json={"token": first, **payload})
    ).status_code == 400
    assert (
        await client.post("/api/auth/reset-password", json={"token": second, **payload})
    ).status_code == 200


@pytest.mark.asyncio
async def test_expired_reset_token_is_rejected(
    client: AsyncClient, outbox: list, db_session: AsyncSession
):
    await register(client, "expired@example.com")
    outbox.clear()
    await client.post(
        "/api/auth/forgot-password", json={"email": "expired@example.com"}
    )
    await db_session.execute(
        update(EmailToken)
        .where(EmailToken.purpose == "password_reset")
        .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    await db_session.commit()
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token_from(outbox[0]), "password": "brand_new_password_987"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_is_rate_limited(client: AsyncClient, outbox: list):
    statuses = [
        (
            await client.post(
                "/api/auth/forgot-password", json={"email": "spam@example.com"}
            )
        ).status_code
        for _ in range(7)
    ]
    assert statuses[:5] == [200] * 5
    assert 429 in statuses[5:]


def test_email_sender_selection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.services.email.settings.EMAIL_BACKEND", "log")
    assert isinstance(get_email_sender(), LogEmailSender)
    monkeypatch.setattr("app.services.email.settings.EMAIL_BACKEND", "smtp")
    monkeypatch.setattr("app.services.email.settings.SMTP_HOST", "smtp.example.com")
    assert isinstance(get_email_sender(), SmtpEmailSender)


@pytest.mark.asyncio
async def test_password_reset_revokes_existing_sessions(
    client: AsyncClient, outbox: list
):
    await register(client, "revoke@example.com")
    old_cookie = client.cookies.get("access_token")
    assert (await client.get("/api/auth/me")).json()["email"] == "revoke@example.com"

    outbox.clear()
    await client.post("/api/auth/forgot-password", json={"email": "revoke@example.com"})
    reset = await client.post(
        "/api/auth/reset-password",
        json={"token": token_from(outbox[0]), "password": "brand_new_password_987"},
    )
    assert reset.status_code == 200

    # The pre-reset session no longer authenticates.
    client.cookies.set("access_token", old_cookie)
    assert (await client.get("/api/auth/me")).json() is None

    client.cookies.clear()
    login = await client.post(
        "/api/auth/login",
        json={"email": "revoke@example.com", "password": "brand_new_password_987"},
    )
    assert login.status_code == 200
    assert (await client.get("/api/auth/me")).json()["email"] == "revoke@example.com"
