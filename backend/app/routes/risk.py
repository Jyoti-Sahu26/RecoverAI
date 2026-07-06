from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import CameraScan, DailyLog, Patient, WearableMetric
from app.services.intelligence import medication_adherence
from app.services.risk_engine import calculate_patient_risk

router = APIRouter()


@router.get("/{patient_id}")
def current_risk(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    latest_scan = db.query(CameraScan).filter(CameraScan.patient_id == patient_id).order_by(CameraScan.created_at.desc()).first()
    wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient_id).order_by(WearableMetric.metric_date.asc()).all()
    return calculate_patient_risk(patient, logs, latest_scan, wearables, medication_adherence(db, patient_id))
