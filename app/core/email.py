import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_email_sync(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_failure_email(to: str, job_id: str, job_name: str, error_message: str) -> None:
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD or not settings.SMTP_FROM:
        logger.warning("SMTP settings not configured, skipping failure email")
        return
    
    subject = f"[Chronos] Job '{job_name}' failed permanently"
    body = (
        f"Job '{job_name}' (ID: {job_id}) has exhausted all retries and failed permanently.\n\n"
        f"Error message:\n{error_message}"
    )

    try:
        await asyncio.to_thread(_send_email_sync, to, subject, body)
        logger.info("Failure email sent for job %s", job_id)
    except Exception:
        logger.exception("Failed to send failure email for job %s", job_id)
