"""Pluggable transactional mailer.

V1 ships a `console` backend that logs emails instead of sending them (dev and
tests). The interface is intentionally small so an SMTP / transactional-API
backend (SES, SendGrid) can be dropped in later without touching callers — see
the epic's open question flagged for an ADR.
"""

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

import anyio

from app.core.config import settings

logger = logging.getLogger("app.mailer")


class Mailer(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleMailer:
    """Logs the email to the application logger; never sends externally."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info(
            "EMAIL (console backend)\n  to: %s\n  subject: %s\n  body:\n%s",
            to,
            subject,
            body,
        )


class SmtpMailer:
    """Sends via a plain SMTP server (MailDev in local dev, a provider in prod).

    Uses stdlib smtplib in a worker thread so the async request isn't blocked;
    MailDev accepts unauthenticated mail on port 1025 and shows it in its web UI.
    """

    async def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.mail_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        def _send() -> None:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.send_message(message)

        await anyio.to_thread.run_sync(_send)


def build_verification_email(link: str) -> tuple[str, str]:
    subject = "Vérifiez votre adresse email"
    body = (
        "Bienvenue sur Algeria SeLoger.\n\n"
        "Confirmez votre adresse email en ouvrant le lien ci-dessous "
        "(valable 24h) :\n"
        f"{link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email."
    )
    return subject, body


def build_password_reset_email(link: str) -> tuple[str, str]:
    subject = "Réinitialisation de votre mot de passe"
    body = (
        "Vous avez demandé à réinitialiser votre mot de passe.\n\n"
        "Ouvrez le lien ci-dessous pour en choisir un nouveau "
        "(valable 1h) :\n"
        f"{link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : "
        "votre mot de passe reste inchangé."
    )
    return subject, body


def get_mailer() -> Mailer:
    """FastAPI dependency returning the configured mailer backend."""
    if settings.mailer_backend == "console":
        return ConsoleMailer()
    if settings.mailer_backend == "smtp":
        return SmtpMailer()
    # Fail loud on misconfiguration rather than silently dropping emails.
    raise RuntimeError(f"Unsupported mailer backend: {settings.mailer_backend!r}")
