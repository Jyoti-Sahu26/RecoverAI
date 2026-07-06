from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Alert, CameraScan, DailyLog, Notification, Patient, RecoveryPlan, User, WearableMetric
from app.schemas.schemas import AlertAckPayload
from app.services.intelligence import medication_adherence
from app.services.risk_engine import calculate_patient_risk

router = APIRouter()


def _caregiver_user(db: Session, caregiver_id: int):
    caregiver = db.query(User).filter(User.id == caregiver_id, User.role == "caregiver").first()
    if not caregiver:
        raise HTTPException(status_code=404, detail="Caregiver not found")
    return caregiver


@router.get("/{caregiver_id}/patients")
def caregiver_patients(caregiver_id: int, db: Session = Depends(get_db)):
    _caregiver_user(db, caregiver_id)
    patients = db.query(Patient).filter(Patient.caregiver_id == caregiver_id).all()
    enriched = []
    for patient in patients:
        user = db.query(User).filter(User.id == patient.user_id).first()
        logs = db.query(DailyLog).filter(DailyLog.patient_id == patient.id).order_by(DailyLog.log_date.asc()).all()
        latest_scan = db.query(CameraScan).filter(CameraScan.patient_id == patient.id).order_by(CameraScan.created_at.desc()).first()
        wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient.id).order_by(WearableMetric.metric_date.asc()).all()
        latest_alert = db.query(Alert).filter(Alert.patient_id == patient.id, Alert.target_role == "caregiver").order_by(Alert.created_at.desc()).first()
        enriched.append({
            "patient": patient,
            "user": user,
            "latest_log": logs[-1] if logs else None,
            "latest_risk": calculate_patient_risk(patient, logs, latest_scan, wearables, medication_adherence(db, patient.id)) if logs else None,
            "latest_alert": latest_alert,
        })
    return enriched


@router.get("/{caregiver_id}/alerts")
def caregiver_alerts(caregiver_id: int, db: Session = Depends(get_db)):
    _caregiver_user(db, caregiver_id)
    return db.query(Alert).filter(
        Alert.recipient_user_id == caregiver_id,
        Alert.target_role == "caregiver",
    ).order_by(Alert.created_at.desc()).all()


@router.post("/{caregiver_id}/alerts/acknowledge")
def acknowledge_alert(caregiver_id: int, payload: AlertAckPayload, db: Session = Depends(get_db)):
    _caregiver_user(db, caregiver_id)
    alert = db.query(Alert).filter(Alert.id == payload.alert_id, Alert.recipient_user_id == caregiver_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    alert.status = "acknowledged"
    related_notes = db.query(Notification).filter(Notification.related_alert_id == alert.id, Notification.user_id == caregiver_id).all()
    for note in related_notes:
        note.read = True
    db.commit()
    return {"message": "Alert acknowledged"}


@router.get("/{caregiver_id}/patient-logs")
def caregiver_patient_logs(caregiver_id: int, db: Session = Depends(get_db)):
    _caregiver_user(db, caregiver_id)
    patients = db.query(Patient).filter(Patient.caregiver_id == caregiver_id).all()
    patient_ids = [p.id for p in patients]
    if not patient_ids:
        return []
    return db.query(DailyLog).filter(DailyLog.patient_id.in_(patient_ids)).order_by(DailyLog.created_at.desc()).all()


@router.get("/{caregiver_id}/dashboard")
def caregiver_dashboard(caregiver_id: int, db: Session = Depends(get_db)):
    _caregiver_user(db, caregiver_id)
    patients = db.query(Patient).filter(Patient.caregiver_id == caregiver_id).all()
    patient_ids = [p.id for p in patients]
    alerts = db.query(Alert).filter(
        Alert.recipient_user_id == caregiver_id,
        Alert.target_role == "caregiver",
    ).order_by(Alert.created_at.desc()).all()
    logs = db.query(DailyLog).filter(DailyLog.patient_id.in_(patient_ids)).order_by(DailyLog.log_date.asc()).all() if patient_ids else []
    notes = db.query(Notification).filter(Notification.user_id == caregiver_id).order_by(Notification.created_at.desc()).limit(20).all()

    trend_counts = defaultdict(int)
    for alert in alerts:
        trend_counts[alert.level] += 1

    priority_patients = []
    for patient in patients:
        user = db.query(User).filter(User.id == patient.user_id).first()
        patient_logs = [log for log in logs if log.patient_id == patient.id]
        latest_scan = db.query(CameraScan).filter(CameraScan.patient_id == patient.id).order_by(CameraScan.created_at.desc()).first()
        wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient.id).order_by(WearableMetric.metric_date.asc()).all()
        risk = calculate_patient_risk(patient, patient_logs, latest_scan, wearables, medication_adherence(db, patient.id)) if patient_logs else None
        plan = db.query(RecoveryPlan).filter(RecoveryPlan.patient_id == patient.id).first()
        latest_alert = next((alert for alert in alerts if alert.patient_id == patient.id), None)
        priority_patients.append({
            "patient_id": patient.id,
            "patient_name": user.full_name if user else f"Patient {patient.id}",
            "diagnosis": patient.diagnosis,
            "monitoring_level": patient.monitoring_level,
            "risk": risk,
            "plan_phase": getattr(plan, "phase", None),
            "latest_log_date": patient_logs[-1].log_date if patient_logs else None,
            "has_open_alert": bool(latest_alert and latest_alert.status == "open"),
        })

    priority_patients.sort(key=lambda item: (item["risk"]["risk_score"] if item["risk"] else 0), reverse=True)

    return {
        "counts": {
            "linked_patients": len(patients),
            "active_alerts": len([a for a in alerts if not a.acknowledged]),
            "recent_logs": len(logs),
        },
        "priority_patients": priority_patients,
        "alerts": alerts[:20],
        "notifications": notes,
        "alert_distribution": dict(trend_counts),
    }
