from collections import Counter
from datetime import date, datetime, timedelta, timezone
from statistics import mean

from sqlalchemy.orm import Session

from app.models.models import DailyLog, MedicationIntake, MedicationSchedule, Patient, RecoveryPlan, User, WearableMetric
from app.services.risk_engine import calculate_patient_risk


def split_text(raw: str):
    return [item.strip() for item in (raw or "").split("||") if item.strip()]


def latest_patient_context(db: Session, patient_id: int):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient_id).order_by(WearableMetric.metric_date.asc()).all()
    plan = db.query(RecoveryPlan).filter(RecoveryPlan.patient_id == patient_id).first()
    adherence = medication_adherence(db, patient_id)
    risk = calculate_patient_risk(patient, logs, None, wearables, adherence) if patient else {}
    return patient, logs, wearables, plan, adherence, risk


def medication_adherence(db: Session, patient_id: int):
    schedules = db.query(MedicationSchedule).filter(
        MedicationSchedule.patient_id == patient_id,
        MedicationSchedule.active == True,  # noqa: E712
    ).all()
    since = date.today() - timedelta(days=6)
    intakes = db.query(MedicationIntake).filter(
        MedicationIntake.patient_id == patient_id,
        MedicationIntake.intake_date >= since,
    ).all()
    total_expected = max(len(schedules) * 7, len(intakes), 1)
    taken = len([item for item in intakes if item.taken])
    missed = len([item for item in intakes if not item.taken])
    if not schedules and not intakes:
        score = 100
    else:
        score = round((taken / total_expected) * 100, 1)
    return {
        "active_medications": len(schedules),
        "records_7d": len(intakes),
        "taken_7d": taken,
        "missed_7d": missed,
        "adherence_score": score,
        "status": "excellent" if score >= 90 else "watch" if score >= 70 else "poor",
    }


def wearable_summary(wearables):
    if not wearables:
        return {
            "connected": False,
            "source": "not_connected",
            "avg_heart_rate": 0,
            "avg_sleep": 0,
            "avg_steps": 0,
            "avg_stress": 0,
            "avg_spo2": 0,
            "trend": "No wearable samples available.",
        }
    recent = wearables[-7:]
    avg_sleep = round(mean([item.sleep_hours for item in recent]), 1)
    avg_stress = round(mean([item.stress_level for item in recent]), 1)
    avg_steps = int(mean([item.steps for item in recent]))
    avg_spo2 = round(mean([item.oxygen_saturation for item in recent if item.oxygen_saturation] or [0]), 1)
    source_counts = Counter([item.source for item in recent])
    trend = "Wearable indicators are stable."
    if avg_sleep < 6 and avg_stress >= 7:
        trend = "Sleep is low while stress is high, which can increase relapse risk."
    elif avg_steps < 1000:
        trend = "Activity is low; gentle movement may need attention."
    elif avg_spo2 and avg_spo2 < 94:
        trend = "Oxygen saturation is below the preferred recovery range."
    return {
        "connected": True,
        "source": source_counts.most_common(1)[0][0],
        "avg_heart_rate": int(mean([item.heart_rate for item in recent if item.heart_rate] or [0])),
        "avg_sleep": avg_sleep,
        "avg_steps": avg_steps,
        "avg_stress": avg_stress,
        "avg_spo2": avg_spo2,
        "trend": trend,
    }


def predict_relapse(patient, logs, wearables, adherence):
    if not patient or not logs:
        return {
            "probability": 0,
            "risk_level": "unknown",
            "horizon_days": 2,
            "trend": "Need daily logs before prediction.",
            "drivers": ["Submit symptoms for at least two days."],
        }

    recent_logs = logs[-5:]
    recent_wearables = wearables[-5:] if wearables else []
    score = 8
    drivers = []

    if len(recent_logs) >= 2 and recent_logs[-1].pain_score > recent_logs[0].pain_score:
        score += 18
        drivers.append("Pain is trending upward.")
    if len(recent_logs) >= 2 and recent_logs[-1].mobility_score < recent_logs[0].mobility_score:
        score += 14
        drivers.append("Mobility is declining.")
    if mean([log.sleep_hours for log in recent_logs]) < getattr(patient, "target_sleep_hours", 8) - 1:
        score += 12
        drivers.append("Sleep is below the personalized target.")
    if any(log.temperature >= 100.4 for log in recent_logs):
        score += 18
        drivers.append("Fever-level temperature appears in recent logs.")
    if adherence.get("adherence_score", 100) < 75:
        score += 15
        drivers.append("Medication adherence is below the safe range.")
    if recent_wearables:
        if mean([item.stress_level for item in recent_wearables]) >= 7:
            score += 11
            drivers.append("Wearable stress level is elevated.")
        if mean([item.sleep_hours for item in recent_wearables]) < 6:
            score += 10
            drivers.append("Wearable sleep trend is low.")
        spo2_values = [item.oxygen_saturation for item in recent_wearables if item.oxygen_saturation]
        if spo2_values and mean(spo2_values) < 94:
            score += 14
            drivers.append("Oxygen saturation trend is below target.")

    probability = min(96, score)
    level = "high" if probability >= 65 else "moderate" if probability >= 35 else "low"
    trend = "Relapse risk may rise within 48 hours." if level == "high" else "Recovery trend needs routine monitoring." if level == "moderate" else "Relapse risk appears controlled."
    return {
        "probability": round(probability, 1),
        "risk_level": level,
        "horizon_days": 2,
        "trend": trend,
        "drivers": drivers or ["No major negative trend detected."],
    }


def smart_recommendations(patient, logs, wearables, adherence, risk):
    latest = logs[-1] if logs else None
    recommendations = []

    if risk.get("risk_level") in {"high", "critical"}:
        recommendations.append({"category": "clinical", "priority": "urgent", "text": "Contact the caregiver or doctor and repeat a symptom check within 4 hours."})
    if latest and latest.sleep_hours < getattr(patient, "target_sleep_hours", 8):
        recommendations.append({"category": "sleep", "priority": "medium", "text": "Move bedtime earlier and reduce screen exposure for the last 45 minutes."})
    if latest and latest.mobility_score <= 2:
        recommendations.append({"category": "activity", "priority": "medium", "text": "Choose supervised low-intensity movement instead of unsupervised exercise."})
    if latest and latest.mood_score <= 2:
        recommendations.append({"category": "mental health", "priority": "medium", "text": "Try a five-minute breathing routine and share mood notes with the caregiver."})
    if adherence.get("adherence_score", 100) < 90:
        recommendations.append({"category": "medication", "priority": "high", "text": "Use dose reminders today and mark each medicine immediately after taking it."})

    wearable = wearable_summary(wearables)
    if wearable["connected"] and wearable["avg_steps"] < getattr(patient, "target_steps", 2500):
        recommendations.append({"category": "activity", "priority": "low", "text": "Aim for short walking blocks to move closer to the daily step target."})
    if wearable["connected"] and wearable["avg_stress"] >= 7:
        recommendations.append({"category": "stress", "priority": "medium", "text": "Schedule a guided breathing or meditation break before evening."})

    if not recommendations:
        recommendations.append({"category": "recovery", "priority": "low", "text": "Continue the recovery plan, hydration, and daily logging streak."})
    return recommendations[:6]


def recovery_timeline(patient, logs, wearables, adherence):
    points = []
    for log in logs[-30:]:
        health_score = 100
        health_score -= log.pain_score * 4
        health_score -= max(0, log.temperature - 98.6) * 5
        health_score -= max(0, 5 - log.mobility_score) * 5
        health_score -= max(0, getattr(patient, "target_sleep_hours", 8) - log.sleep_hours) * 4
        health_score -= log.meds_missed_count * 5
        points.append({
            "date": str(log.log_date),
            "health_score": round(max(0, min(100, health_score)), 1),
            "risk_score": log.risk_score,
            "pain": log.pain_score,
            "sleep": log.sleep_hours,
        })

    streak = 0
    seen_dates = {log.log_date for log in logs}
    cursor = date.today()
    while cursor in seen_dates:
        streak += 1
        cursor -= timedelta(days=1)

    improvement = 0
    if len(points) >= 2:
        improvement = round(points[-1]["health_score"] - points[0]["health_score"], 1)

    milestones = []
    if streak >= 7:
        milestones.append("7-day symptom logging streak achieved.")
    if adherence.get("adherence_score", 0) >= 90:
        milestones.append("Medication adherence is above 90%.")
    if points and points[-1]["health_score"] >= 80:
        milestones.append("Current recovery health score is in the strong range.")
    if not milestones:
        milestones.append("Complete daily logs to unlock consistency milestones.")

    return {
        "points": points,
        "streak_days": streak,
        "improvement_percent": improvement,
        "milestones": milestones,
    }


def analyze_emotion_text(text: str):
    lowered = text.lower()
    anxious_terms = ["anxious", "panic", "scared", "worried", "fear", "breathless"]
    sad_terms = ["sad", "hopeless", "cry", "depressed", "alone", "low"]
    fatigue_terms = ["tired", "weak", "exhausted", "fatigue", "sleepy"]
    pain_terms = ["pain", "ache", "dizzy", "nausea", "fever"]
    scores = {
        "anxiety": sum(term in lowered for term in anxious_terms),
        "low_mood": sum(term in lowered for term in sad_terms),
        "fatigue": sum(term in lowered for term in fatigue_terms),
        "physical_distress": sum(term in lowered for term in pain_terms),
    }
    dominant = max(scores, key=scores.get)
    if scores[dominant] == 0:
        dominant = "stable"
    sentiment = "negative" if dominant != "stable" else "neutral"
    support = "Escalate to caregiver if this feeling is intense or persistent." if dominant in {"anxiety", "low_mood", "physical_distress"} else "Keep journaling mood with daily symptoms."
    return {"dominant_emotion": dominant, "sentiment": sentiment, "scores": scores, "support_message": support}


def parse_voice_command(transcript: str):
    text = transcript.lower()
    pain = 5
    if "severe" in text or "very bad" in text:
        pain = 8
    elif "mild" in text or "little" in text:
        pain = 3
    mood = 2 if any(word in text for word in ["sad", "anxious", "panic", "low"]) else 3
    mobility = 2 if any(word in text for word in ["cannot walk", "weak", "dizzy"]) else 3
    fatigue = 8 if any(word in text for word in ["tired", "exhausted", "fatigue"]) else 3
    symptom_notes = transcript.strip()
    return {
        "draft_log": {
            "pain_score": pain,
            "mood_score": mood,
            "mobility_score": mobility,
            "fatigue_score": fatigue,
            "symptom_notes": symptom_notes,
            "voice_note": transcript.strip(),
        },
        "detected_symptoms": [word for word in ["headache", "dizziness", "nausea", "fever", "pain", "swelling"] if word in text],
        "confidence": 0.82 if len(text.split()) >= 4 else 0.62,
    }


def assistant_reply(patient, logs, plan, risk, message: str):
    lowered = message.lower()
    safety_level = "standard"
    if any(term in lowered for term in ["chest pain", "faint", "bleeding", "can't breathe", "cannot breathe", "unconscious"]):
        safety_level = "urgent"
        return {
            "reply": "This could be urgent. Please use the SOS option, contact your caregiver or doctor now, or call local emergency services if symptoms are severe.",
            "safety_level": safety_level,
            "actions": ["trigger_sos", "contact_caregiver", "contact_doctor"],
        }

    latest = logs[-1] if logs else None
    plan_tasks = split_text(plan.daily_tasks if plan else "")
    base = []
    if "eat" in lowered or "food" in lowered or "diet" in lowered:
        base.append("Choose light, protein-rich meals, hydration, and doctor-approved foods that do not interfere with medication.")
    if "exercise" in lowered or "walk" in lowered:
        if latest and latest.mobility_score <= 2:
            base.append("Keep exercise gentle today and ask for supervision because mobility is low.")
        else:
            base.append("Short, low-intensity walks are reasonable if pain and dizziness are controlled.")
    if "dizzy" in lowered or "dizziness" in lowered:
        base.append("Dizziness can relate to hydration, sleep, medicines, fever, or low intake. Sit down, hydrate, and log the symptom.")
    if "medicine" in lowered or "medication" in lowered:
        base.append("Follow the prescribed timing and mark each dose in medication tracking so adherence alerts stay accurate.")
    if "risk" in lowered or "score" in lowered:
        base.append(f"Your current risk level is {risk.get('risk_level', 'unknown')} with score {risk.get('risk_score', 0)}.")

    if not base:
        base.append("I reviewed your recovery profile, recent symptoms, risk level, and plan. Keep symptoms logged daily and follow the plan priorities.")
    if risk.get("risk_level") in {"high", "critical"}:
        base.append("Because your risk is elevated, involve your caregiver or doctor instead of waiting.")
    if plan_tasks:
        base.append(f"Today's plan priority: {plan_tasks[0]}")
    return {"reply": " ".join(base), "safety_level": safety_level, "actions": ["log_symptom", "review_plan"]}


def overview_payload(db: Session, patient_id: int):
    patient, logs, wearables, _plan, adherence, risk = latest_patient_context(db, patient_id)
    relapse = predict_relapse(patient, logs, wearables, adherence)
    return {
        "wearable_summary": wearable_summary(wearables),
        "adherence": adherence,
        "prediction": relapse,
        "recommendations": smart_recommendations(patient, logs, wearables, adherence, risk),
        "timeline": recovery_timeline(patient, logs, wearables, adherence),
        "xai": risk.get("xai_factors", []),
        "risk": risk,
    }


def demo_wearable_metric(patient_id: int):
    today = date.today()
    return WearableMetric(
        patient_id=patient_id,
        source="Google Fit demo",
        metric_date=today,
        heart_rate=78,
        sleep_hours=6.4,
        steps=3200,
        stress_level=5,
        oxygen_saturation=97,
        hrv_score=52,
    )
