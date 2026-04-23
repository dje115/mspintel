import secrets
from datetime import UTC, datetime, timedelta
import smtplib
from email.message import EmailMessage

from app.core.settings import get_settings

settings = get_settings()


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def build_invite_accept_url(token: str | None = None) -> str:
    base = f"{settings.frontend_app_url}/accept-invitation"
    if token:
        return f"{base}?token={token}"
    return base


class MailService:
    def send(self, to_email: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.mail_from_email
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(settings.mail_smtp_host, settings.mail_smtp_port, timeout=10) as smtp:
            if settings.mail_use_tls:
                smtp.starttls()
            if settings.mail_smtp_username:
                smtp.login(settings.mail_smtp_username, settings.mail_smtp_password)
            smtp.send_message(msg)


def invitation_email_body(tenant_name: str, role_code: str, token: str, expires_at: datetime) -> str:
    accept_url = build_invite_accept_url(token)
    return (
        f"You were invited to join {tenant_name} on MSPIntel.\n"
        f"Assigned role: {role_code}\n"
        f"Accept invitation: {accept_url}\n"
        f"Invite token: {token}\n"
        f"Expires at: {expires_at.isoformat()}\n"
    )


def invitation_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=settings.invitation_ttl_hours)
