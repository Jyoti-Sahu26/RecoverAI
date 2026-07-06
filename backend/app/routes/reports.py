import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import DailyLog, DoctorNote, MedicationIntake, MedicationSchedule, Patient, User
from app.services.intelligence import overview_payload
from app.services.notifications import patient_display_name
from app.services.security import record_audit

router = APIRouter()


def _wrap(text: str, width: int = 88):
    words = str(text or "").replace("\n", " ").split()
    lines = []
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines or [""]


def _pdf_escape(text: str):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(title: str, lines):
    content_lines = ["BT", "/F1 11 Tf", "50 780 Td"]
    first = True
    for raw in lines[:52]:
        for line in _wrap(raw):
            if first:
                first = False
            else:
                content_lines.append("0 -15 Td")
            content_lines.append(f"({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{idx} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R /Info << /Title ({_pdf_escape(title)}) >> >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)


@router.get("/patient/{patient_id}/pdf")
def patient_pdf_report(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    user = db.query(User).filter(User.id == patient.user_id).first()
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.desc()).limit(14).all()
    meds = db.query(MedicationSchedule).filter(MedicationSchedule.patient_id == patient_id, MedicationSchedule.active == True).all()  # noqa: E712
    notes = db.query(DoctorNote).filter(DoctorNote.patient_id == patient_id).order_by(DoctorNote.created_at.desc()).limit(5).all()
    overview = overview_payload(db, patient_id)

    lines = [
        "RecoverAI Predictive Recovery Report",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Patient: {user.full_name if user else patient_display_name(db, patient)}",
        f"Diagnosis: {patient.diagnosis}",
        f"Current Risk: {overview['risk'].get('risk_level')} ({overview['risk'].get('risk_score')})",
        f"Relapse Forecast: {overview['prediction']['risk_level']} - {overview['prediction']['probability']}% within {overview['prediction']['horizon_days']} days",
        f"Medication Adherence: {overview['adherence']['adherence_score']}%",
        f"Wearable Summary: {overview['wearable_summary']['trend']}",
        "Top Explainability Factors:",
    ]
    lines.extend([f"- {item.get('feature')}: {item.get('reason')} (+{item.get('impact')})" for item in overview.get("xai", [])[:6]])
    lines.append("Smart Recommendations:")
    lines.extend([f"- {item['category']}: {item['text']}" for item in overview.get("recommendations", [])])
    lines.append("Recent Symptoms:")
    lines.extend([f"- {log.log_date}: pain {log.pain_score}, temp {log.temperature}, sleep {log.sleep_hours}, risk {log.risk_score}" for log in logs])
    lines.append("Medications:")
    lines.extend([f"- {med.medicine_name} {med.dosage} at {med.timing}" for med in meds] or ["- No active medications recorded."])
    lines.append("Doctor Notes:")
    lines.extend([f"- {note.created_at}: {note.summary}" for note in notes] or ["- No doctor notes recorded."])

    record_audit(db, "pdf_report_generated", "patient", patient_id)
    db.commit()
    filename = f"recoverai_patient_{patient_id}_report.pdf"
    return Response(
        content=_simple_pdf("RecoverAI Report", lines),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/patient/{patient_id}/csv")
def patient_csv_export(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    intakes = db.query(MedicationIntake).filter(MedicationIntake.patient_id == patient_id).order_by(MedicationIntake.intake_date.asc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["type", "date", "metric", "value", "notes"])
    for log in logs:
        writer.writerow(["daily_log", log.log_date, "risk_score", log.risk_score, log.risk_explanation])
        writer.writerow(["daily_log", log.log_date, "pain_score", log.pain_score, log.symptom_notes])
        writer.writerow(["daily_log", log.log_date, "sleep_hours", log.sleep_hours, ""])
    for intake in intakes:
        writer.writerow(["medication", intake.intake_date, intake.medicine_name, "taken" if intake.taken else "missed", intake.notes])
    record_audit(db, "csv_export_generated", "patient", patient_id)
    db.commit()
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="recoverai_patient_{patient_id}_export.csv"'},
    )
