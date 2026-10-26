"""
Real SMTP email sending (password reset) — stdlib smtplib, no extra
dependency. There's no mock/fake mode: if SMTP isn't configured,
send_email() raises EmailNotConfiguredError rather than pretending a
message went out, matching how app/rag/gemini_client.py handles a missing
Gemini key.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailNotConfiguredError(Exception):
    pass


class EmailSendError(Exception):
    pass


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise EmailNotConfiguredError(
            "Email sending is not configured on this server (set SMTP_HOST and SMTP_FROM_EMAIL in .env)."
        )

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(f"Could not send email: {exc}") from exc
