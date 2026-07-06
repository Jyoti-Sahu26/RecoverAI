import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import OTPRequest, SessionToken, User
from app.schemas.schemas import OTPEmailOnlyPayload, OTPRequestPayload, OTPVerifyPayload, PasswordResetPayload, RefreshTokenPayload, UserLogin
from app.services.notifications import dump_meta, load_meta, send_email
from app.services.security import create_access_token, create_refresh_token, hash_token, record_audit, verify_access_token

router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
def _create_otp(db: Session, email: str, purpose: str, meta: dict = None):
    db.query(OTPRequest).filter(
        OTPRequest.email == email,
        OTPRequest.purpose == purpose,
        OTPRequest.consumed == False,  # noqa: E712
    ).update({"consumed": True})
    otp = f"{secrets.randbelow(900000) + 100000}"
    record = OTPRequest(
        email=email,
        otp_code=otp,
        purpose=purpose,
        meta_json=dump_meta(meta or {}),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        consumed=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, otp


@router.post("/request-otp")
def request_otp(payload: OTPRequestPayload, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    record, otp = _create_otp(
        db,
        email,
        "register",
        {
            "full_name": payload.full_name,
            "email": email,
            "password_hash": pwd_context.hash(payload.password),
            "role": payload.role,
            "phone": payload.phone,
        },
    )
    sent = send_email(
        "RecoverAI registration OTP",
        f"Your RecoverAI registration OTP is {otp}. It expires in 10 minutes.",
        email,
    )
    if not sent:
        record.consumed = True
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Set SMTP environment variables to send OTP by email.",
        )

    return {
        "message": "OTP sent successfully to your email.",
        "expires_in_minutes": 10,
        "otp_request_id": record.id,
    }


@router.post("/verify-otp-register")
def verify_otp_and_register(payload: OTPVerifyPayload, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    otp_record = (
        db.query(OTPRequest)
        .filter(OTPRequest.email == email, OTPRequest.purpose == "register")
        .order_by(OTPRequest.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP request not found")
    if otp_record.consumed:
        raise HTTPException(status_code=400, detail="OTP already used")
    if otp_record.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    if otp_record.otp_code != payload.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp_meta = load_meta(otp_record.meta_json)
    if (otp_meta.get("email") or "").strip().lower() != email:
        raise HTTPException(status_code=400, detail="OTP email mismatch")
    full_name = (otp_meta.get("full_name") or "").strip()
    role = (otp_meta.get("role") or "").strip().lower()
    password_hash = otp_meta.get("password_hash")
    if not password_hash and otp_meta.get("password"):
        password_hash = pwd_context.hash(otp_meta["password"])
    if not full_name or role not in {"patient", "caregiver", "doctor", "admin"} or not password_hash:
        raise HTTPException(status_code=400, detail="Stored OTP registration data is invalid. Request a new OTP.")

    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role=role,
        phone=otp_meta.get("phone"),
        otp_verified=True,
    )
    db.add(user)
    db.flush()
    otp_record.consumed = True
    record_audit(db, "user_registered", "user", user.id, user.id, {"role": user.role})
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "role": user.role,
        "full_name": user.full_name,
        "email": user.email,
    }


@router.post("/request-password-reset")
def request_password_reset(payload: OTPEmailOnlyPayload, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    record, otp = _create_otp(db, email, "reset_password")
    sent = send_email(
        "RecoverAI password reset OTP",
        f"Your RecoverAI password reset OTP is {otp}. It expires in 10 minutes.",
        email,
    )
    if not sent:
        record.consumed = True
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Set SMTP environment variables to send OTP by email.",
        )
    return {"message": "Password reset OTP sent to your email."}


@router.post("/reset-password")
def reset_password(payload: PasswordResetPayload, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_record = (
        db.query(OTPRequest)
        .filter(OTPRequest.email == email, OTPRequest.purpose == "reset_password")
        .order_by(OTPRequest.created_at.desc())
        .first()
    )
    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP request not found")
    if otp_record.consumed:
        raise HTTPException(status_code=400, detail="OTP already used")
    if otp_record.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    if otp_record.otp_code != payload.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.password_hash = pwd_context.hash(payload.new_password)
    otp_record.consumed = True
    record_audit(db, "password_reset", "user", user.id, user.id)
    db.commit()
    return {"message": "Password reset successful."}


@router.post("/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(db, user)
    record_audit(db, "user_login", "user", user.id, user.id)
    db.commit()

    return {
        "message": "Login successful",
        "user_id": user.id,
        "role": user.role,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh_token(payload: RefreshTokenPayload, db: Session = Depends(get_db)):
    record = db.query(SessionToken).filter(
        SessionToken.refresh_token_hash == hash_token(payload.refresh_token),
        SessionToken.revoked == False,  # noqa: E712
    ).first()
    if not record or record.expires_at.replace(tzinfo=None) < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")
    user = db.query(User).filter(User.id == record.user_id, User.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.get("/me")
def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "").strip()
    data = verify_access_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == int(data["sub"]), User.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "user_id": user.id,
        "role": user.role,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
    }


@router.post("/logout")
def logout(payload: RefreshTokenPayload, db: Session = Depends(get_db)):
    record = db.query(SessionToken).filter(SessionToken.refresh_token_hash == hash_token(payload.refresh_token)).first()
    if record:
        record.revoked = True
        record_audit(db, "user_logout", "user", record.user_id, record.user_id)
        db.commit()
    return {"message": "Logged out"}
