from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import (
    Alert,
    EmergencyEvent,
    MedicationIntake,
    MedicationSchedule,
    Patient,
    User,
    WearableMetric,
)
from app.schemas.schemas import (
    EmergencyPayload,
    EmotionPayload,
    MedicationIntakePayload,
    VoiceCommandPayload,
    WearableMetricPayload,
)
from app.services.intelligence import (
    analyze_emotion_text,
    demo_wearable_metric,
    medication_adherence,
    overview_payload,
    parse_voice_command,
)
from app.services.notifications import create_notification, patient_display_name
from app.services.security import record_audit

router = APIRouter()


def _patient(db: Session, patient_id: int):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/patients/{patient_id}/overview")
def intelligence_overview(patient_id: int, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    return overview_payload(db, patient_id)


@router.get("/patients/{patient_id}/wearables")
def wearable_metrics(patient_id: int, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    return db.query(WearableMetric).filter(WearableMetric.patient_id == patient_id).order_by(WearableMetric.metric_date.asc()).all()


@router.post("/patients/{patient_id}/wearables")
def add_wearable_metric(patient_id: int, payload: WearableMetricPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    metric = WearableMetric(patient_id=patient_id, **payload.model_dump())
    db.add(metric)
    record_audit(db, "wearable_metric_added", "patient", patient_id, metadata={"source": payload.source})
    db.commit()
    db.refresh(metric)
    return {"message": "Wearable metric stored", "metric": metric, "overview": overview_payload(db, patient_id)}


@router.post("/patients/{patient_id}/wearables/sync-demo")
def sync_demo_wearable(patient_id: int, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    metric = demo_wearable_metric(patient_id)
    db.add(metric)
    record_audit(db, "wearable_demo_sync", "patient", patient_id)
    db.commit()
    db.refresh(metric)
    return {"message": "Demo wearable sample synced", "metric": metric, "overview": overview_payload(db, patient_id)}


@router.get("/patients/{patient_id}/medications/adherence")
def adherence(patient_id: int, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    intakes = db.query(MedicationIntake).filter(MedicationIntake.patient_id == patient_id).order_by(MedicationIntake.intake_date.desc()).limit(50).all()
    return {"summary": medication_adherence(db, patient_id), "intakes": intakes}


@router.post("/patients/{patient_id}/medications/intake")
def mark_medication_intake(patient_id: int, payload: MedicationIntakePayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    schedule = None
    if payload.schedule_id:
        schedule = db.query(MedicationSchedule).filter(
            MedicationSchedule.id == payload.schedule_id,
            MedicationSchedule.patient_id == patient_id,
        ).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Medication schedule not found")

    intake = MedicationIntake(
        patient_id=patient_id,
        schedule_id=payload.schedule_id,
        intake_date=payload.intake_date,
        medicine_name=schedule.medicine_name if schedule else payload.medicine_name,
        taken=payload.taken,
        taken_at=datetime.now(timezone.utc) if payload.taken else None,
        notes=payload.notes,
    )
    db.add(intake)
    record_audit(db, "medication_intake_recorded", "patient", patient_id, metadata={"taken": payload.taken})
    db.commit()
    db.refresh(intake)
    return {"message": "Medication intake recorded", "intake": intake, "adherence": medication_adherence(db, patient_id)}


@router.post("/patients/{patient_id}/voice-command")
def voice_command(patient_id: int, payload: VoiceCommandPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    result = parse_voice_command(payload.transcript)
    record_audit(db, "voice_command_parsed", "patient", patient_id, metadata={"confidence": result["confidence"]})
    db.commit()
    return result


@router.post("/patients/{patient_id}/emotion")
def emotion_analysis(patient_id: int, payload: EmotionPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    result = analyze_emotion_text(payload.text)
    record_audit(db, "emotion_text_analyzed", "patient", patient_id, metadata={"dominant": result["dominant_emotion"]})
    db.commit()
    return result


@router.post("/patients/{patient_id}/emergency")
def emergency_sos(patient_id: int, payload: EmergencyPayload, db: Session = Depends(get_db)):
    patient = _patient(db, patient_id)
    event = EmergencyEvent(patient_id=patient_id, **payload.model_dump())
    db.add(event)
    db.flush()

    patient_name = patient_display_name(db, patient)
    recipients = []
    if patient.caregiver_id:
        caregiver = db.query(User).filter(User.id == patient.caregiver_id).first()
        if caregiver:
            recipients.append(caregiver)
    if patient.doctor_id:
        doctor = db.query(User).filter(User.id == patient.doctor_id).first()
        if doctor:
            recipients.append(doctor)
    recipients.extend(db.query(User).filter(User.role == "admin", User.is_active == True).all())  # noqa: E712

    reason = payload.message or "Emergency support requested."
    location = f" Location: {payload.latitude}, {payload.longitude}." if payload.latitude and payload.longitude else ""
    for recipient in recipients:
        alert = Alert(
            patient_id=patient_id,
            recipient_user_id=recipient.id,
            level=payload.severity,
            reason=reason,
            explanation=f"SOS triggered for {patient_name}.{location}",
            target_role=recipient.role,
            status="open",
            acknowledged=False,
        )
        db.add(alert)
        db.flush()
        create_notification(
            db,
            user_id=recipient.id,
            patient_id=patient_id,
            kind="emergency_sos",
            title=f"SOS: {patient_name}",
            message=f"{reason}{location}",
            channel="sms_whatsapp_push_email",
            email_to=recipient.email,
            related_alert_id=alert.id,
            try_send_email=True,
        )

    record_audit(db, "emergency_sos_triggered", "patient", patient_id, payload.triggered_by_user_id, {"event_id": event.id})
    db.commit()
    db.refresh(event)
    return {
        "message": "Emergency SOS triggered",
        "event": event,
        "notified_users": [{"id": user.id, "name": user.full_name, "role": user.role} for user in recipients],
        "nearest_hospitals_hint": [
            "City General Hospital - emergency department",
            "RecoverAI Partner Clinic - urgent recovery review",
            "Nearest available hospital based on shared location",
        ],
    }
