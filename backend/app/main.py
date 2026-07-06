from datetime import date, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.models.models import Alert, DailyLog, Notification, Patient, User
from app.routes import advanced, admin, assistant, auth, caregivers, doctors, intelligence, notifications, patients, reports, risk
from app.services.intelligence import overview_payload
from app.services.notifications import create_notification, patient_display_name

Base.metadata.create_all(bind=engine)


def ensure_columns():
    inspector = inspect(engine)
    migrations = {
        "users": {
            "phone": "ALTER TABLE users ADD COLUMN phone VARCHAR",
            "otp_verified": "ALTER TABLE users ADD COLUMN otp_verified BOOLEAN DEFAULT 0",
            "is_active": "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
        },
        "otp_requests": {
            "meta_json": "ALTER TABLE otp_requests ADD COLUMN meta_json TEXT DEFAULT ''",
        },
        "patients": {
            "onboarding_completed": "ALTER TABLE patients ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0",
            "doctor_id": "ALTER TABLE patients ADD COLUMN doctor_id INTEGER",
            "emergency_contact_name": "ALTER TABLE patients ADD COLUMN emergency_contact_name VARCHAR DEFAULT ''",
            "emergency_contact_phone": "ALTER TABLE patients ADD COLUMN emergency_contact_phone VARCHAR DEFAULT ''",
            "location_consent": "ALTER TABLE patients ADD COLUMN location_consent BOOLEAN DEFAULT 0",
            "health_goal": "ALTER TABLE patients ADD COLUMN health_goal TEXT DEFAULT ''",
            "preferred_language": "ALTER TABLE patients ADD COLUMN preferred_language VARCHAR DEFAULT 'English'",
            "accessibility_mode": "ALTER TABLE patients ADD COLUMN accessibility_mode VARCHAR DEFAULT 'standard'",
            "monitoring_level": "ALTER TABLE patients ADD COLUMN monitoring_level VARCHAR DEFAULT 'standard'",
            "recovery_type": "ALTER TABLE patients ADD COLUMN recovery_type VARCHAR DEFAULT 'guided'",
            "target_sleep_hours": "ALTER TABLE patients ADD COLUMN target_sleep_hours FLOAT DEFAULT 8",
            "target_steps": "ALTER TABLE patients ADD COLUMN target_steps INTEGER DEFAULT 2500",
            "notes": "ALTER TABLE patients ADD COLUMN notes TEXT DEFAULT ''",
            "reminder_time": "ALTER TABLE patients ADD COLUMN reminder_time VARCHAR DEFAULT '20:00'",
            "created_at": "ALTER TABLE patients ADD COLUMN created_at DATETIME",
        },
        "daily_logs": {
            "fatigue_score": "ALTER TABLE daily_logs ADD COLUMN fatigue_score INTEGER DEFAULT 0",
            "swelling_score": "ALTER TABLE daily_logs ADD COLUMN swelling_score INTEGER DEFAULT 0",
            "wound_score": "ALTER TABLE daily_logs ADD COLUMN wound_score INTEGER DEFAULT 0",
            "voice_note": "ALTER TABLE daily_logs ADD COLUMN voice_note TEXT DEFAULT ''",
            "risk_score": "ALTER TABLE daily_logs ADD COLUMN risk_score FLOAT DEFAULT 0",
            "risk_level": "ALTER TABLE daily_logs ADD COLUMN risk_level VARCHAR DEFAULT 'unknown'",
            "risk_explanation": "ALTER TABLE daily_logs ADD COLUMN risk_explanation TEXT DEFAULT ''",
            "risk_recommendations": "ALTER TABLE daily_logs ADD COLUMN risk_recommendations TEXT DEFAULT ''",
        },
        "alerts": {
            "target_role": "ALTER TABLE alerts ADD COLUMN target_role VARCHAR DEFAULT 'caregiver'",
            "recipient_user_id": "ALTER TABLE alerts ADD COLUMN recipient_user_id INTEGER",
            "acknowledged": "ALTER TABLE alerts ADD COLUMN acknowledged BOOLEAN DEFAULT 0",
        },
        "notifications": {
            "provider_status": "ALTER TABLE notifications ADD COLUMN provider_status VARCHAR DEFAULT 'queued'",
            "external_reference": "ALTER TABLE notifications ADD COLUMN external_reference VARCHAR DEFAULT ''",
        },
    }

    with engine.begin() as conn:
        for table_name, columns in migrations.items():
            if table_name not in inspector.get_table_names():
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for col_name, stmt in columns.items():
                if col_name not in existing_columns:
                    conn.execute(text(stmt))


ensure_columns()
Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def send_patient_log_reminders():
    db: Session = SessionLocal()
    try:
        today = date.today()
        patients_all = db.query(Patient).filter(Patient.onboarding_completed == True).all()  # noqa: E712
        for patient in patients_all:
            user = db.query(User).filter(User.id == patient.user_id).first()
            if not user:
                continue
            has_today_log = db.query(DailyLog).filter(DailyLog.patient_id == patient.id, DailyLog.log_date == today).first()
            if not has_today_log:
                create_notification(
                    db,
                    user_id=user.id,
                    patient_id=patient.id,
                    kind="daily_log_reminder",
                    title="Daily symptom log reminder",
                    message="Please complete your mandatory daily symptom log today.",
                    channel="email_and_in_app",
                    email_to=user.email,
                    try_send_email=True,
                )
        db.commit()
    finally:
        db.close()


def send_caregiver_missed_alert_reminders():
    db: Session = SessionLocal()
    try:
        threshold = datetime.utcnow() - timedelta(hours=2)
        alerts = db.query(Alert).filter(
            Alert.target_role == "caregiver",
            Alert.acknowledged == False,
            Alert.created_at <= threshold,
            Alert.level.in_(["high", "critical"]),
        ).all()
        for alert in alerts:
            caregiver = db.query(User).filter(User.id == alert.recipient_user_id).first()
            patient = db.query(Patient).filter(Patient.id == alert.patient_id).first()
            if not caregiver or not patient:
                continue
            create_notification(
                db,
                user_id=caregiver.id,
                patient_id=patient.id,
                kind="missed_alert_reminder",
                title="Missed patient alert reminder",
                message=f"You still have an unacknowledged {alert.level} alert for {patient_display_name(db, patient)}.",
                channel="email_and_in_app",
                email_to=caregiver.email,
                related_alert_id=alert.id,
                try_send_email=True,
            )
        db.commit()
    finally:
        db.close()


def send_predictive_relapse_notifications():
    db: Session = SessionLocal()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        patients_all = db.query(Patient).filter(Patient.onboarding_completed == True).all()  # noqa: E712
        for patient in patients_all:
            user = db.query(User).filter(User.id == patient.user_id).first()
            if not user:
                continue
            overview = overview_payload(db, patient.id)
            prediction = overview.get("prediction", {})
            already_sent = db.query(Notification).filter(
                Notification.user_id == user.id,
                Notification.patient_id == patient.id,
                Notification.kind == "predictive_relapse",
                Notification.created_at >= today_start,
            ).first()
            if prediction.get("risk_level") == "high" and not already_sent:
                create_notification(
                    db,
                    user_id=user.id,
                    patient_id=patient.id,
                    kind="predictive_relapse",
                    title="Predictive relapse warning",
                    message=prediction.get("trend", "Relapse risk may rise soon."),
                    channel="push_email_in_app",
                    email_to=user.email,
                    try_send_email=True,
                )
        db.commit()
    finally:
        db.close()


app = FastAPI(title="RecoverAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(caregivers.router, prefix="/api/caregivers", tags=["Caregivers"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["AI Assistant"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["Predictive Intelligence"])
app.include_router(doctors.router, prefix="/api/doctors", tags=["Doctors"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(advanced.router, prefix="/api/advanced", tags=["Advanced Recovery"])


@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(send_patient_log_reminders, "cron", hour=20, minute=0, id="patient_log_reminders", replace_existing=True)
        scheduler.add_job(send_caregiver_missed_alert_reminders, "interval", hours=1, id="caregiver_alert_reminders", replace_existing=True)
        scheduler.add_job(send_predictive_relapse_notifications, "interval", hours=6, id="predictive_relapse_notifications", replace_existing=True)
        scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/")
def root():
    return {"message": "RecoverAI backend is running"}
