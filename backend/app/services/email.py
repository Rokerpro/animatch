"""Transactional email behind a small sender interface."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    """Sends a plain-text email."""

    async def send(self, to: str, subject: str, body: str) -> None: ...


class LogEmailSender:
    """Development sender that records the message in the application log."""

    async def send(self, to: str, subject: str, body: str) -> None:
        logger.info("Email to %s | %s\n%s", to, subject, body)


class SmtpEmailSender:
    """Sends email through an SMTP server without blocking the event loop."""

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_STARTTLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)

    async def send(self, to: str, subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_sync, to, subject, body)


def get_email_sender() -> EmailSender:
    """Return the configured sender; SMTP requires SMTP_HOST."""
    if settings.EMAIL_BACKEND == "smtp" and settings.SMTP_HOST:
        return SmtpEmailSender()
    return LogEmailSender()


async def send_email_safely(to: str, subject: str, body: str) -> None:
    """Send an email, logging failures instead of surfacing provider details."""
    try:
        await get_email_sender().send(to, subject, body)
    except Exception:
        logger.exception("Failed to send email to %s", to)
