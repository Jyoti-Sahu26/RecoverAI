import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import AuditLog, SessionToken, User
from app.services.notifications import dump_meta

JWT_SECRET = os.getenv("JWT_SECRET", "recoverai-dev-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_json(data: dict) -> str:
    return _b64(json.dumps(data, separators=(",", ":")).encode())


def _sign(message: str) -> str:
    return _b64(hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest())


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp()),
    }
    unsigned = f"{_b64_json(header)}.{_b64_json(payload)}"
    return f"{unsigned}.{_sign(unsigned)}"


def verify_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        unsigned = f"{header}.{payload}"
        if not hmac.compare_digest(_sign(unsigned), signature):
            return {}
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if data.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
            return {}
        return data
    except Exception:
        return {}


def create_refresh_token(db: Session, user: User, user_agent: str = "") -> str:
    token = secrets.token_urlsafe(48)
    record = SessionToken(
        user_id=user.id,
        refresh_token_hash=hash_token(token),
        user_agent=user_agent,
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    db.add(record)
    db.flush()
    return token


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def record_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: int = None,
    actor_user_id: int = None,
    metadata: dict = None,
):
    event = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=dump_meta(metadata or {}),
    )
    db.add(event)
    db.flush()
    return event
