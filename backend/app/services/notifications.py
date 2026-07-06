import json
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Notification, Patient, User


def _load_backend_env_file():
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_backend_env_file()

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME or "noreply@recoverai.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
DEV_SHOW_OTP = os.getenv("DEV_SHOW_OTP", "false").lower() == "true"


def send_email(subject: str, body: str, to_email: str) -> bool:
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        if DEV_SHOW_OTP:
            print(f"[RecoverAI email dev mode] To: {to_email} | Subject: {subject}\n{body}\n")
        else:
            print(f"[RecoverAI email disabled] Configure SMTP settings to send '{subject}' to {to_email}.")
        return DEV_SHOW_OTP

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
    return True


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    kind: str,
    channel: str = "in_app",
    email_to: Optional[str] = None,
    patient_id: Optional[int] = None,
    related_alert_id: Optional[int] = None,
    try_send_email: bool = False,
):
    note = Notification(
        user_id=user_id,
        patient_id=patient_id,
        kind=kind,
        title=title,
        message=message,
        channel=channel,
        email_to=email_to,
        related_alert_id=related_alert_id,
        sent=False,
        read=False,
        provider_status="queued",
    )
    db.add(note)
    db.flush()

    if try_send_email and email_to:
        ok = send_email(title, message, email_to)
        if ok:
            note.sent = True
            note.sent_at = datetime.now(timezone.utc)
            note.provider_status = "sent"
        else:
            note.provider_status = "provider_failed"
    elif channel != "in_app":
        print(f"[RecoverAI notification dev mode] Channel: {channel} | User: {user_id} | {title}: {message}")
        note.provider_status = "dev_simulated"
        note.sent = True
        note.sent_at = datetime.now(timezone.utc)
    else:
        note.provider_status = "in_app_ready"
    return note


def dump_meta(data) -> str:
    return json.dumps(data)


def load_meta(raw: str):
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


def patient_display_name(db: Session, patient: Patient) -> str:
    user = db.query(User).filter(User.id == patient.user_id).first()
    return user.full_name if user else f"Patient {patient.id}"
