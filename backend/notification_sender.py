"""
Email Sender

Sends real emails via Gmail SMTP (smtplib, no extra dependency needed).
Credentials are read from environment variables only - never hardcoded,
never logged, never returned in any API response.

Required in your .env file:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USERNAME=youraddress@gmail.com
    SMTP_PASSWORD=your-16-character-app-password
    SMTP_FROM_NAME=AI Resume Screening System

If these aren't set, send_email() raises a clear error rather than
silently failing or pretending to succeed - a notification system that
fails silently is worse than one that fails loudly, since the former
hides exactly the kind of problem the audit log exists to catch.
"""
from __future__ import annotations
import os
import smtplib
import ssl
from email.message import EmailMessage

MAX_RETRIES = 3


class EmailSendError(Exception):
    """Raised when an email genuinely fails to send after all retries."""
    pass


class EmailConfigError(Exception):
    """Raised when SMTP credentials are missing or incomplete."""
    pass


def get_smtp_config() -> dict:
    host      = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port      = int(os.getenv("SMTP_PORT", "587"))
    username  = os.getenv("SMTP_USERNAME")
    password  = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("SMTP_FROM_NAME", "AI Resume Screening System")

    if not username or not password:
        raise EmailConfigError(
            "SMTP_USERNAME and SMTP_PASSWORD must be set in .env before "
            "any email can be sent. See notification_sender.py docstring "
            "for the full list of required environment variables."
        )

    return {
        "host": host, "port": port,
        "username": username, "password": password,
        "from_name": from_name,
    }


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Send a single plain-text email. Raises EmailSendError if it fails
    after MAX_RETRIES attempts, EmailConfigError if credentials are
    missing entirely. Does NOT write to NotificationLog itself - that's
    the caller's responsibility (see notification_service.py), keeping
    this module a pure "send one email" primitive that's easy to test
    and easy to swap out later if you move off Gmail SMTP.
    """
    config = get_smtp_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"]    = f'{config["from_name"]} <{config["username"]}>'
    message["To"]       = to_email
    message.set_content(body)

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(config["host"], config["port"], timeout=15) as server:
                server.starttls(context=context)
                server.login(config["username"], config["password"])
                server.send_message(message)
            return  # success - stop retrying
        except smtplib.SMTPAuthenticationError as e:
            # Auth errors will never succeed on retry (wrong password is
            # wrong on every attempt) - fail immediately rather than
            # waste two more attempts and make the caller wait longer
            # for a result that was never going to change.
            raise EmailSendError(
                f"SMTP authentication failed. Check SMTP_USERNAME and "
                f"SMTP_PASSWORD (must be a Gmail App Password, not your "
                f"regular account password). Original error: {e}"
            ) from e
        except (smtplib.SMTPException, OSError) as e:
            last_error = e
            continue  # transient - worth retrying

    raise EmailSendError(
        f"Failed to send email to {to_email} after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )