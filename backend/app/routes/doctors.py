from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Appointment, DailyLog, DoctorNote, Patient, User
from app.schemas.schemas import AppointmentPayload, DoctorNotePayload
from app.services.intelligence import overview_payload
from app.services.notifications import create_notification, patient_display_name
from app.services.security import record_audit

router = APIRouter()


def _doctor(db: Session, doctor_id: int):
    doctor = db.query(User).filter(User.id == doctor_id, User.role == "doctor").first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.get("/options")
def doctor_options(db: Session = Depends(get_db)):
    doctors = db.query(User).filter(User.role == "doctor", User.is_active == True).order_by(User.full_name.asc()).all()  # noqa: E712
    return [{"id": doctor.id, "full_name": doctor.full_name, "email": doctor.email, "phone": doctor.phone} for doctor in doctors]


@router.get("/{doctor_id}/dashboard")
def doctor_dashboard(doctor_id: int, db: Session = Depends(get_db)):
    _doctor(db, doctor_id)
    assigned = db.query(Patient).filter(Patient.doctor_id == doctor_id).all()
    if not assigned:
        assigned = db.query(Patient).order_by(Patient.id.desc()).limit(12).all()

    patients = []
    for patient in assigned:
        user = db.query(User).filter(User.id == patient.user_id).first()
        overview = overview_payload(db, patient.id)
        latest_log = db.query(DailyLog).filter(DailyLog.patient_id == patient.id).order_by(DailyLog.log_date.desc()).first()
        patients.append({
            "patient": patient,
            "user": user,
            "latest_log": latest_log,
            "risk": overview["risk"],
            "prediction": overview["prediction"],
            "adherence": overview["adherence"],
        })

    notes = db.query(DoctorNote).filter(DoctorNote.doctor_user_id == doctor_id).order_by(DoctorNote.created_at.desc()).limit(30).all()
    appointments = db.query(Appointment).filter(Appointment.doctor_user_id == doctor_id).order_by(Appointment.scheduled_at.asc()).limit(30).all()
    high_risk = len([item for item in patients if item["risk"].get("risk_level") in {"high", "critical"}])
    return {
        "counts": {
            "assigned_patients": len(assigned),
            "high_risk": high_risk,
            "appointments": len(appointments),
            "notes": len(notes),
        },
        "patients": patients,
        "notes": notes,
        "appointments": appointments,
    }


@router.post("/{doctor_id}/notes")
def add_doctor_note(doctor_id: int, payload: DoctorNotePayload, db: Session = Depends(get_db)):
    doctor = _doctor(db, doctor_id)
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    note = DoctorNote(doctor_user_id=doctor_id, **payload.model_dump())
    db.add(note)
    create_notification(
        db,
        user_id=patient.user_id,
        patient_id=patient.id,
        kind="doctor_note",
        title=f"New doctor note from {doctor.full_name}",
        message=payload.summary[:280],
        channel="in_app",
        email_to=None,
    )
    record_audit(db, "doctor_note_created", "patient", patient.id, doctor_id, {"note_type": payload.note_type})
    db.commit()
    db.refresh(note)
    return {"message": "Doctor note saved", "note": note}


@router.post("/{doctor_id}/appointments")
def schedule_appointment(doctor_id: int, payload: AppointmentPayload, db: Session = Depends(get_db)):
    doctor = _doctor(db, doctor_id)
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    appointment = Appointment(doctor_user_id=doctor_id, **payload.model_dump())
    db.add(appointment)
    patient_user = db.query(User).filter(User.id == patient.user_id).first()
    create_notification(
        db,
        user_id=patient.user_id,
        patient_id=patient.id,
        kind="appointment",
        title=f"Appointment scheduled with {doctor.full_name}",
        message=f"{patient_display_name(db, patient)} has an appointment for {payload.scheduled_at}.",
        channel="email_and_in_app",
        email_to=patient_user.email if patient_user else None,
        try_send_email=True,
    )
    record_audit(db, "appointment_scheduled", "patient", patient.id, doctor_id)
    db.commit()
    db.refresh(appointment)
    return {"message": "Appointment scheduled", "appointment": appointment}
