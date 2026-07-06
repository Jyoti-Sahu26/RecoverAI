from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Alert, AuditLog, DailyLog, EmergencyEvent, Notification, Patient, User, WearableMetric

router = APIRouter()


@router.get("/summary")
def admin_summary(db: Session = Depends(get_db)):
    total_patients = db.query(Patient).count()
    total_alerts = db.query(Alert).count()
    critical_alerts = db.query(Alert).filter(Alert.level == "critical").count()
    total_logs = db.query(DailyLog).count()
    total_users = db.query(User).count()
    caregivers = db.query(User).filter(User.role == "caregiver").count()
    doctors = db.query(User).filter(User.role == "doctor").count()
    unread_notifications = db.query(Notification).filter(Notification.read == False).count()  # noqa: E712
    emergency_events = db.query(EmergencyEvent).count()

    return {
        "total_patients": total_patients,
        "total_alerts": total_alerts,
        "critical_alerts": critical_alerts,
        "total_logs": total_logs,
        "total_users": total_users,
        "caregivers": caregivers,
        "doctors": doctors,
        "unread_notifications": unread_notifications,
        "emergency_events": emergency_events,
    }


@router.get("/alerts")
def admin_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).filter(Alert.target_role == "admin").order_by(Alert.created_at.desc()).all()


@router.get("/patients")
def admin_patients(db: Session = Depends(get_db)):
    return db.query(Patient).order_by(Patient.id.desc()).all()


@router.get("/logs")
def admin_logs(db: Session = Depends(get_db)):
    return db.query(DailyLog).order_by(DailyLog.created_at.desc()).all()


@router.get("/notifications")
def admin_notifications(db: Session = Depends(get_db)):
    return db.query(Notification).order_by(Notification.created_at.desc()).limit(50).all()


@router.get("/analytics")
def admin_analytics(db: Session = Depends(get_db)):
    alerts = db.query(Alert).all()
    logs = db.query(DailyLog).order_by(DailyLog.log_date.asc()).all()
    patients = db.query(Patient).all()
    wearables = db.query(WearableMetric).all()
    audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(25).all()

    risk_distribution = defaultdict(int)
    alert_frequency = defaultdict(int)
    recovery_scores = []
    for alert in alerts:
        risk_distribution[alert.level] += 1
        if alert.created_at:
            alert_frequency[str(alert.created_at.date())] += 1
    for log in logs:
        if log.risk_score is not None:
            recovery_scores.append(max(0, 100 - log.risk_score))

    success_rate = round(len([score for score in recovery_scores if score >= 65]) / max(len(recovery_scores), 1) * 100, 1)
    recent_trend = [
        {
            "date": str(log.log_date),
            "risk_score": log.risk_score,
            "pain": log.pain_score,
            "sleep": log.sleep_hours,
        }
        for log in logs[-30:]
    ]
    return {
        "kpis": {
            "active_users": db.query(User).filter(User.is_active == True).count(),  # noqa: E712
            "risk_distribution": dict(risk_distribution),
            "recovery_success_rate": success_rate,
            "alert_count": len(alerts),
            "wearable_samples": len(wearables),
            "patient_count": len(patients),
        },
        "alert_frequency": [{"date": key, "alerts": value} for key, value in sorted(alert_frequency.items())],
        "recent_recovery_trend": recent_trend,
        "audit_logs": audits,
    }
