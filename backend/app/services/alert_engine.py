from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.models import Alert, Patient, User
from app.services.notifications import create_notification, patient_display_name


def _create_alert(
    db: Session,
    patient_id: int,
    level: str,
    reason: str,
    explanation: str,
    target_role: str,
    recipient_user_id: int = None,
):
    alert = Alert(
        patient_id=patient_id,
        recipient_user_id=recipient_user_id,
        level=level,
        reason=reason,
        explanation=explanation,
        target_role=target_role,
        status="open",
        acknowledged=False,
    )
    db.add(alert)
    db.flush()
    return alert


def sync_alerts(db: Session, patient: Patient, risk_result: Dict) -> List[Alert]:
    level = risk_result.get("risk_level")
    if level not in {"high", "critical"}:
        return []

    reason = "; ".join(risk_result.get("explanation", [])[:5]) or "High-risk recovery pattern detected."
    explanation = "; ".join(risk_result.get("recommendations_common", [])[:4]) or "Review the patient urgently."

    created = []
    existing_open = db.query(Alert).filter(
        Alert.patient_id == patient.id,
        Alert.level == level,
        Alert.status == "open",
    ).order_by(Alert.created_at.desc()).all()
    open_roles = {(a.target_role, a.recipient_user_id) for a in existing_open}
    patient_name = patient_display_name(db, patient)

    if patient.caregiver_id and ("caregiver", patient.caregiver_id) not in open_roles:
        caregiver = db.query(User).filter(User.id == patient.caregiver_id, User.role == "caregiver").first()
        if caregiver:
            alert = _create_alert(db, patient.id, level, reason, explanation, "caregiver", caregiver.id)
            create_notification(
                db,
                user_id=caregiver.id,
                patient_id=patient.id,
                kind="caregiver_alert",
                title=f"Emergency alert for {patient_name}",
                message=f"{patient_name} is at {level} risk. Reason: {reason}",
                channel="email_and_in_app",
                email_to=caregiver.email,
                related_alert_id=alert.id,
                try_send_email=True,
            )
            created.append(alert)

    admin_users = db.query(User).filter(User.role == "admin", User.is_active == True).all()  # noqa: E712
    for admin in admin_users:
        if ("admin", admin.id) not in open_roles:
            alert = _create_alert(db, patient.id, level, reason, explanation, "admin", admin.id)
            create_notification(
                db,
                user_id=admin.id,
                patient_id=patient.id,
                kind="admin_alert",
                title=f"Admin alert: {patient_name}",
                message=f"{patient_name} is at {level} risk. Reason: {reason}",
                channel="in_app",
                email_to=admin.email,
                related_alert_id=alert.id,
                try_send_email=False,
            )
            created.append(alert)

    patient_user = db.query(User).filter(User.id == patient.user_id).first()
    if patient_user:
        create_notification(
            db,
            user_id=patient_user.id,
            patient_id=patient.id,
            kind="patient_risk_result",
            title=f"Your latest risk score is {risk_result.get('risk_score')}",
            message="; ".join(risk_result.get("explanation", [])[:4]),
            channel="in_app",
            email_to=patient_user.email,
            try_send_email=False,
        )

    if created:
        db.commit()
        for alert in created:
            db.refresh(alert)
    else:
        db.commit()
    return created
