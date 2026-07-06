from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import ChatMessage, Patient
from app.schemas.schemas import AssistantChatPayload
from app.services.intelligence import assistant_reply, latest_patient_context
from app.services.notifications import dump_meta
from app.services.security import record_audit

router = APIRouter()


@router.post("/patient/{patient_id}/chat")
def chat_with_assistant(patient_id: int, payload: AssistantChatPayload, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    _patient, logs, _wearables, plan, _adherence, risk = latest_patient_context(db, patient_id)
    result = assistant_reply(patient, logs, plan, risk, payload.message)
    chat = ChatMessage(
        patient_id=patient_id,
        user_id=payload.user_id,
        sender="patient",
        message=payload.message,
        response=result["reply"],
        safety_level=result["safety_level"],
        context_json=dump_meta({"risk_level": risk.get("risk_level"), "actions": result["actions"]}),
    )
    db.add(chat)
    record_audit(db, "assistant_chat", "patient", patient_id, payload.user_id, {"safety_level": result["safety_level"]})
    db.commit()
    db.refresh(chat)
    return {
        "message_id": chat.id,
        "reply": result["reply"],
        "safety_level": result["safety_level"],
        "suggested_actions": result["actions"],
        "context": {"risk_level": risk.get("risk_level"), "risk_score": risk.get("risk_score")},
    }


@router.get("/patient/{patient_id}/history")
def assistant_history(patient_id: int, db: Session = Depends(get_db)):
    return db.query(ChatMessage).filter(ChatMessage.patient_id == patient_id).order_by(ChatMessage.created_at.desc()).limit(30).all()
