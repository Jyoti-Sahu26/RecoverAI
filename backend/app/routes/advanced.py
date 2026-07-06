import asyncio
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db
from app.models.models import (
    CollaborationItem,
    CommunityPost,
    CommunityThread,
    HabitEntry,
    HealthJournalEntry,
    MealPlan,
    MedicalRecord,
    MedicationSchedule,
    Patient,
    PrescriptionScan,
    RecoveryGoal,
)
from app.schemas.schemas import (
    AdaptiveCheckinPayload,
    CameraSeverityPayload,
    CollaborationPayload,
    CommunityPostPayload,
    CommunityThreadPayload,
    GoalPayload,
    HabitEntryPayload,
    JournalEntryPayload,
    MealPlanPayload,
    MedicalRecordPayload,
    PrescriptionScanPayload,
    SimulationPayload,
)
from app.services.advanced_engine import (
    adaptive_questions,
    advanced_hub_payload,
    camera_severity_payload,
    extract_prescription,
    journal_ai_payload,
    meal_plan_payload,
    risk_map_payload,
    simulation_payload,
)
from app.services.notifications import dump_meta
from app.services.security import record_audit

router = APIRouter()


def _patient(db: Session, patient_id: int):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _moderate_text(text: str):
    lowered = (text or "").lower()
    blocked = ["self harm", "suicide", "kill myself", "hate speech", "abuse"]
    return "needs_review" if any(term in lowered for term in blocked) else "approved"


@router.get("/patients/{patient_id}/hub")
def advanced_hub(patient_id: int, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    payload = advanced_hub_payload(db, patient_id)
    record_audit(db, "advanced_hub_viewed", "patient", patient_id)
    db.commit()
    return payload


@router.post("/patients/{patient_id}/habits")
def add_habit(patient_id: int, payload: HabitEntryPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    entry = HabitEntry(patient_id=patient_id, **payload.model_dump())
    db.add(entry)
    record_audit(db, "habit_entry_added", "patient", patient_id)
    db.commit()
    db.refresh(entry)
    return {"message": "Habit entry saved", "entry": entry, "hub": advanced_hub_payload(db, patient_id)}


@router.post("/patients/{patient_id}/journal")
def add_journal(patient_id: int, payload: JournalEntryPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    analysis = journal_ai_payload(payload.text)
    entry = HealthJournalEntry(
        patient_id=patient_id,
        user_id=payload.user_id,
        journal_date=payload.journal_date,
        text=payload.text,
        sentiment=analysis["sentiment"],
        emotion=analysis["dominant_emotion"],
        stress_score=analysis["stress_score"],
        ai_insight=analysis["insight"],
    )
    db.add(entry)
    record_audit(db, "journal_added", "patient", patient_id, payload.user_id, {"emotion": analysis["dominant_emotion"]})
    db.commit()
    db.refresh(entry)
    return {"message": "Journal saved", "entry": entry, "analysis": analysis}


@router.post("/patients/{patient_id}/collaboration")
def add_collaboration(patient_id: int, payload: CollaborationPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    item = CollaborationItem(patient_id=patient_id, **payload.model_dump())
    db.add(item)
    record_audit(db, "collaboration_item_added", "patient", patient_id, payload.created_by_user_id, {"item_type": payload.item_type})
    db.commit()
    db.refresh(item)
    return {"message": "Collaboration item saved", "item": item}


@router.post("/patients/{patient_id}/meal-plan")
def generate_meal_plan(patient_id: int, payload: MealPlanPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    plan = meal_plan_payload(db, patient_id, payload.allergies, payload.nutrition_goal)
    record = MealPlan(
        patient_id=patient_id,
        plan_date=payload.plan_date,
        allergies=payload.allergies,
        nutrition_goal=payload.nutrition_goal,
        meals_json=dump_meta(plan["meals"]),
        hydration_plan=plan["hydration_plan"],
        ai_reason=plan["ai_reason"],
    )
    db.add(record)
    record_audit(db, "meal_plan_generated", "patient", patient_id)
    db.commit()
    db.refresh(record)
    return {"message": "AI meal plan generated", "plan": plan, "record_id": record.id}


@router.post("/patients/{patient_id}/goals")
def add_goal(patient_id: int, payload: GoalPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    progress = 0 if payload.target_value == 0 else min(100, round((payload.current_value / payload.target_value) * 100, 1))
    goal = RecoveryGoal(
        patient_id=patient_id,
        goal_type=payload.goal_type,
        target_value=payload.target_value,
        unit=payload.unit,
        current_value=payload.current_value,
        status="achieved" if progress >= 100 else "active",
        ai_tip=f"You are {progress}% toward your {payload.goal_type} goal.",
    )
    db.add(goal)
    record_audit(db, "recovery_goal_added", "patient", patient_id)
    db.commit()
    db.refresh(goal)
    return {"message": "Recovery goal saved", "goal": goal}


@router.post("/patients/{patient_id}/records")
def add_medical_record(patient_id: int, payload: MedicalRecordPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    summary = "AI summary: "
    summary += payload.content_text[:240] if payload.content_text else "Record uploaded and ready for OCR/doctor review."
    record = MedicalRecord(
        patient_id=patient_id,
        uploaded_by_user_id=payload.uploaded_by_user_id,
        record_type=payload.record_type,
        file_name=payload.file_name,
        content_text=payload.content_text,
        encrypted_reference=f"vault://patient-{patient_id}/{payload.file_name or 'record'}",
        ocr_text=payload.content_text,
        ai_summary=summary,
    )
    db.add(record)
    record_audit(db, "medical_record_added", "patient", patient_id, payload.uploaded_by_user_id, {"record_type": payload.record_type})
    db.commit()
    db.refresh(record)
    return {"message": "Medical record stored in secure vault", "record": record}


@router.post("/patients/{patient_id}/prescription-scan")
def prescription_scan(patient_id: int, payload: PrescriptionScanPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    extraction = extract_prescription(payload.raw_text)
    scan = PrescriptionScan(
        patient_id=patient_id,
        raw_text=payload.raw_text,
        extracted_medicines_json=dump_meta(extraction["medicines"]),
        confidence=extraction["confidence"],
    )
    db.add(scan)
    added = []
    if payload.auto_add_medications:
        for med in extraction["medicines"]:
            schedule = MedicationSchedule(
                patient_id=patient_id,
                medicine_name=med["medicine_name"],
                dosage=med["dosage"],
                timing=med["timing"],
                instructions=med["instructions"],
            )
            db.add(schedule)
            added.append(schedule)
    record_audit(db, "prescription_scanned", "patient", patient_id, metadata={"medicines": len(extraction["medicines"])})
    db.commit()
    db.refresh(scan)
    return {"message": "Prescription OCR completed", "scan": scan, "extraction": extraction, "auto_added": len(added)}


@router.post("/patients/{patient_id}/simulate")
def simulate_recovery(patient_id: int, payload: SimulationPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    return simulation_payload(
        db,
        patient_id,
        sleep_gain=payload.sleep_gain_hours,
        adherence_gain=payload.medication_adherence_gain,
        exercise_gain=payload.exercise_gain_minutes,
        stress_reduction=payload.stress_reduction,
    )


@router.post("/patients/{patient_id}/adaptive-checkin")
def adaptive_checkin(patient_id: int, payload: AdaptiveCheckinPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    return adaptive_questions(db, patient_id, payload.symptom_hint)


@router.post("/patients/{patient_id}/camera-severity")
def camera_severity(patient_id: int, payload: CameraSeverityPayload, db: Session = Depends(get_db)):
    _patient(db, patient_id)
    result = camera_severity_payload(
        redness=payload.redness_index,
        swelling=payload.swelling_index,
        discoloration=payload.discoloration_index,
        pain_expression=payload.pain_expression_index,
        image_type=payload.image_type,
    )
    record_audit(db, "camera_severity_analyzed", "patient", patient_id, metadata=result)
    db.commit()
    return result


@router.post("/community/threads")
def create_thread(payload: CommunityThreadPayload, db: Session = Depends(get_db)):
    moderation = _moderate_text(f"{payload.title} {payload.body}")
    thread = CommunityThread(**payload.model_dump(), ai_moderation=moderation)
    db.add(thread)
    record_audit(db, "community_thread_created", "community", actor_user_id=payload.user_id, metadata={"moderation": moderation})
    db.commit()
    db.refresh(thread)
    return {"message": "Community thread created", "thread": thread}


@router.post("/community/threads/{thread_id}/posts")
def create_post(thread_id: int, payload: CommunityPostPayload, db: Session = Depends(get_db)):
    thread = db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Community thread not found")
    moderation = _moderate_text(payload.body)
    post = CommunityPost(thread_id=thread_id, user_id=payload.user_id, body=payload.body, ai_moderation=moderation)
    db.add(post)
    record_audit(db, "community_post_created", "community", thread_id, payload.user_id, {"moderation": moderation})
    db.commit()
    db.refresh(post)
    return {"message": "Community post created", "post": post}


@router.get("/community/threads")
def list_threads(db: Session = Depends(get_db)):
    return db.query(CommunityThread).order_by(CommunityThread.created_at.desc()).limit(30).all()


@router.get("/admin/risk-map")
def admin_risk_map(db: Session = Depends(get_db)):
    return risk_map_payload(db)


@router.websocket("/patients/{patient_id}/live")
async def patient_live_dashboard(websocket: WebSocket, patient_id: int):
    await websocket.accept()
    try:
        for _ in range(10):
            db = SessionLocal()
            try:
                payload = advanced_hub_payload(db, patient_id)
                db.commit()
                await websocket.send_json({
                    "patient_id": patient_id,
                    "timestamp": str(date.today()),
                    "recovery_score": payload["recovery_score"],
                    "digital_twin": payload["digital_twin"],
                    "smart_notifications": payload["smart_notifications"],
                })
            finally:
                db.close()
            await asyncio.sleep(5)
    except Exception:
        await websocket.close()
