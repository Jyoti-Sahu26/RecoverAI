from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Alert, CameraScan, DailyLog, MedicationSchedule, Patient, RecoveryPlan, User, WearableMetric
from app.schemas.schemas import CameraScanPayload, DailyLogCreate, PatientOnboarding
from app.services.alert_engine import sync_alerts
from app.services.camera_monitor import analyze_camera_scan
from app.services.notifications import create_notification
from app.services.intelligence import medication_adherence, overview_payload
from app.services.plan_generator import generate_profile, generate_recovery_plan
from app.services.risk_engine import calculate_patient_risk
from app.services.security import record_audit

router = APIRouter()


def patient_by_user_id(user_id: int, db: Session):
    return db.query(Patient).filter(Patient.user_id == user_id).first()


@router.get("/profile/by-user/{user_id}")
def get_patient_profile_by_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    patient = patient_by_user_id(user_id, db)
    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        },
        "patient": patient,
    }


@router.get("/caregivers/options")
def caregiver_options(db: Session = Depends(get_db)):
    caregivers = db.query(User).filter(User.role == "caregiver", User.is_active == True).order_by(User.full_name.asc()).all()  # noqa: E712
    return [
        {"id": caregiver.id, "full_name": caregiver.full_name, "email": caregiver.email, "phone": caregiver.phone}
        for caregiver in caregivers
    ]


@router.post("/onboard/{user_id}")
def onboard_patient(user_id: int, payload: PatientOnboarding, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role == "patient").first()
    if not user:
        raise HTTPException(status_code=404, detail="Patient user not found")

    existing = patient_by_user_id(user_id, db)
    if existing:
        raise HTTPException(status_code=400, detail="Patient is already onboarded")

    caregiver_id = payload.caregiver_id
    if caregiver_id is not None:
        caregiver = db.query(User).filter(User.id == caregiver_id, User.role == "caregiver").first()
        if not caregiver:
            raise HTTPException(status_code=400, detail="Selected caregiver not found")

    doctor_id = payload.doctor_id
    if doctor_id is not None:
        doctor = db.query(User).filter(User.id == doctor_id, User.role == "doctor").first()
        if not doctor:
            raise HTTPException(status_code=400, detail="Selected doctor not found")

    profile = generate_profile(payload.age, payload.diagnosis, payload.surgery_type, payload.comorbidities)

    patient = Patient(
        user_id=user_id,
        age=payload.age,
        gender=payload.gender,
        diagnosis=payload.diagnosis,
        surgery_type=payload.surgery_type,
        discharge_date=payload.discharge_date,
        comorbidities=",".join(payload.comorbidities),
        caregiver_id=caregiver_id,
        baseline_risk=profile["baseline_risk"],
        onboarding_completed=True,
        doctor_id=doctor_id,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        location_consent=payload.location_consent,
        health_goal=payload.health_goal,
        preferred_language=payload.preferred_language,
        accessibility_mode=payload.accessibility_mode,
        monitoring_level=profile["monitoring_level"],
        recovery_type=profile["recovery_type"],
        target_sleep_hours=payload.target_sleep_hours,
        target_steps=payload.target_steps,
        notes=payload.notes,
        reminder_time=payload.reminder_time,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    plan_data = generate_recovery_plan(payload, profile)
    plan = RecoveryPlan(
        patient_id=patient.id,
        phase=plan_data["phase"],
        summary=plan_data["summary"],
        daily_tasks="||".join(plan_data["daily_tasks"]),
        precautions="||".join(plan_data["precautions"]),
        reminder_frequency=plan_data["reminder_frequency"],
    )
    db.add(plan)

    for med in payload.medications:
        if med.get("medicine_name") and med.get("dosage") and med.get("timing"):
            db.add(
                MedicationSchedule(
                    patient_id=patient.id,
                    medicine_name=med["medicine_name"],
                    dosage=med["dosage"],
                    timing=med["timing"],
                    instructions=med.get("instructions", ""),
                )
            )

    create_notification(
        db,
        user_id=user.id,
        patient_id=patient.id,
        kind="onboarding_complete",
        title="Onboarding completed",
        message="Your profile and recovery plan are ready on the dashboard.",
        channel="in_app",
        email_to=user.email,
        try_send_email=False,
    )
    if doctor_id:
        create_notification(
            db,
            user_id=doctor_id,
            patient_id=patient.id,
            kind="doctor_assignment",
            title="New patient assigned",
            message=f"{user.full_name} has assigned you as doctor in RecoverAI.",
            channel="in_app",
            email_to=None,
            try_send_email=False,
        )
    record_audit(db, "patient_onboarded", "patient", patient.id, user.id, {"caregiver_id": caregiver_id, "doctor_id": doctor_id})
    db.commit()
    return {"message": "Patient onboarding completed", "patient_id": patient.id, "profile": profile}


@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/by-user/{user_id}/dashboard")
def patient_dashboard(user_id: int, db: Session = Depends(get_db)):
    patient = patient_by_user_id(user_id, db)
    if not patient:
        return {"onboarding_required": True}

    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient.id).order_by(DailyLog.log_date.asc()).all()
    alerts = db.query(Alert).filter(Alert.patient_id == patient.id).order_by(Alert.created_at.desc()).all()
    meds = db.query(MedicationSchedule).filter(MedicationSchedule.patient_id == patient.id, MedicationSchedule.active == True).all()  # noqa: E712
    plan = db.query(RecoveryPlan).filter(RecoveryPlan.patient_id == patient.id).first()
    latest_scan = db.query(CameraScan).filter(CameraScan.patient_id == patient.id).order_by(CameraScan.created_at.desc()).first()
    wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient.id).order_by(WearableMetric.metric_date.asc()).all()
    adherence = medication_adherence(db, patient.id)
    risk = calculate_patient_risk(patient, logs, latest_scan, wearables, adherence) if logs else None
    has_today_log = any(log.log_date == date.today() for log in logs)
    advanced = overview_payload(db, patient.id)

    return {
        "onboarding_required": False,
        "patient": patient,
        "plan": {
            "phase": getattr(plan, "phase", None),
            "summary": getattr(plan, "summary", None),
            "daily_tasks": plan.daily_tasks.split("||") if plan and plan.daily_tasks else [],
            "precautions": plan.precautions.split("||") if plan and plan.precautions else [],
            "reminder_frequency": getattr(plan, "reminder_frequency", None),
        },
        "medications": meds,
        "alerts": alerts[:10],
        "logs": logs,
        "latest_risk": risk,
        "advanced": advanced,
        "latest_scan": latest_scan,
        "has_today_log": has_today_log,
    }


@router.post("/{patient_id}/camera-scan")
def add_camera_scan(patient_id: int, payload: CameraScanPayload, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    preview = type("ScanObj", (), payload.model_dump())
    analysis = analyze_camera_scan(preview)
    scan = CameraScan(
        patient_id=patient_id,
        redness_index=payload.redness_index,
        swelling_index=payload.swelling_index,
        fatigue_index=payload.fatigue_index,
        pain_face_index=payload.pain_face_index,
        skin_tone_index=payload.skin_tone_index,
        hints="||".join(analysis["hints"]),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return {"message": "Camera scan stored", "analysis": analysis, "scan": scan}


@router.post("/{patient_id}/daily-log")
def add_daily_log(patient_id: int, payload: DailyLogCreate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing = db.query(DailyLog).filter(DailyLog.patient_id == patient_id, DailyLog.log_date == payload.log_date).first()
    if existing:
        raise HTTPException(status_code=400, detail="Daily log already submitted for this date")

    log = DailyLog(patient_id=patient_id, **payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)

    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    latest_scan = db.query(CameraScan).filter(CameraScan.patient_id == patient_id).order_by(CameraScan.created_at.desc()).first()
    wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient_id).order_by(WearableMetric.metric_date.asc()).all()
    adherence = medication_adherence(db, patient_id)
    result = calculate_patient_risk(patient, logs, latest_scan, wearables, adherence)

    log.risk_score = result["risk_score"]
    log.risk_level = result["risk_level"]
    log.risk_explanation = "||".join(result["explanation"])
    log.risk_recommendations = "||".join(result["recommendations_common"] + result["recommendations_personalized"])
    db.commit()
    db.refresh(log)

    created_alerts = sync_alerts(db, patient, result)
    record_audit(db, "daily_log_submitted", "patient", patient_id, patient.user_id, {"risk_level": result["risk_level"], "risk_score": result["risk_score"]})
    db.commit()

    return {
        "message": "Daily log added",
        "log_id": log.id,
        "risk": result,
        "risk_stored": True,
        "alert_created": bool(created_alerts),
        "alert_targets": [
            {"id": alert.id, "role": alert.target_role, "recipient_user_id": alert.recipient_user_id}
            for alert in created_alerts
        ],
    }


@router.get("/{patient_id}/logs")
def get_logs(patient_id: int, db: Session = Depends(get_db)):
    return db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
