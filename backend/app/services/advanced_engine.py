import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.models.models import (
    Alert,
    CollaborationItem,
    DailyLog,
    DigitalTwinSnapshot,
    HabitEntry,
    HealthJournalEntry,
    MealPlan,
    MedicalRecord,
    MedicationIntake,
    Patient,
    PrescriptionScan,
    RecoveryGoal,
    RecoveryScoreSnapshot,
    WearableMetric,
)
from app.services.intelligence import analyze_emotion_text, medication_adherence, overview_payload
from app.services.notifications import dump_meta, load_meta


def _latest(items, default=None):
    return items[-1] if items else default


def _level(score):
    if score >= 80:
        return "Stable"
    if score >= 60:
        return "Improving"
    if score >= 40:
        return "At Risk"
    return "Critical Attention"


def recovery_score_payload(db: Session, patient_id: int):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    habits = db.query(HabitEntry).filter(HabitEntry.patient_id == patient_id).order_by(HabitEntry.habit_date.asc()).all()
    wearables = db.query(WearableMetric).filter(WearableMetric.patient_id == patient_id).order_by(WearableMetric.metric_date.asc()).all()
    adherence = medication_adherence(db, patient_id)
    recent = logs[-7:]

    if not patient or not logs:
        components = {"symptoms": 60, "sleep": 50, "habits": 50, "medication": adherence["adherence_score"], "activity": 50}
    else:
        pain_avg = mean([log.pain_score for log in recent])
        sleep_avg = mean([log.sleep_hours for log in recent])
        severity_avg = mean([log.fatigue_score + log.swelling_score + log.wound_score for log in recent]) / 3
        wearable_steps = mean([w.steps for w in wearables[-7:]] or [getattr(patient, "target_steps", 2500) * 0.5])
        habit_quality = mean([min(100, h.water_glasses * 8 + h.meditation_minutes + h.exercise_minutes + h.sleep_quality * 5) for h in habits[-7:]] or [55])
        components = {
            "symptoms": max(0, 100 - pain_avg * 5 - severity_avg * 4),
            "sleep": min(100, (sleep_avg / max(getattr(patient, "target_sleep_hours", 8), 1)) * 100),
            "habits": min(100, habit_quality),
            "medication": adherence["adherence_score"],
            "activity": min(100, (wearable_steps / max(getattr(patient, "target_steps", 2500), 1)) * 100),
        }

    score = round(sum(components.values()) / len(components), 1)
    insights = [
        f"Medication adherence contributes {round(components['medication'], 1)} points.",
        f"Sleep quality contributes {round(components['sleep'], 1)} points.",
        "Symptoms and habits are weighted together for a startup-style recovery score.",
    ]
    return {"score": score, "status": _level(score), "components": components, "insights": insights}


def save_recovery_score_snapshot(db: Session, patient_id: int):
    payload = recovery_score_payload(db, patient_id)
    snapshot = RecoveryScoreSnapshot(
        patient_id=patient_id,
        score_date=date.today(),
        score=payload["score"],
        status=payload["status"],
        components_json=dump_meta(payload["components"]),
        insights="||".join(payload["insights"]),
    )
    db.add(snapshot)
    db.flush()
    return snapshot, payload


def digital_twin_payload(db: Session, patient_id: int):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    overview = overview_payload(db, patient_id)
    score = recovery_score_payload(db, patient_id)

    if not patient or not logs:
        return {
            "recovery_velocity": 0,
            "relapse_probability": overview["prediction"]["probability"],
            "projected_recovery_days": 0,
            "slowdown_risk": 0,
            "summary": "Digital twin needs symptom history to personalize projections.",
            "signals": ["Submit daily logs and wearable data."],
        }

    recent = logs[-7:]
    older = logs[-14:-7] or recent
    recent_health = mean([100 - log.risk_score for log in recent])
    older_health = mean([100 - log.risk_score for log in older])
    velocity = round(recent_health - older_health, 1)
    sleep_avg = mean([log.sleep_hours for log in recent])
    slowdown = max(0, round((getattr(patient, "target_sleep_hours", 8) - sleep_avg) * 9, 1))
    projected = max(7, int(45 - velocity * 2 + overview["prediction"]["probability"] / 3 + slowdown / 2))
    summary = f"Based on recent history, recovery velocity is {velocity}. Recovery may slow by {slowdown}% if sleep remains below target."
    signals = [
        f"Relapse probability: {overview['prediction']['probability']}%",
        f"Recovery score: {score['score']}/100",
        f"Projected recovery window: {projected} days",
    ]
    return {
        "recovery_velocity": velocity,
        "relapse_probability": overview["prediction"]["probability"],
        "projected_recovery_days": projected,
        "slowdown_risk": slowdown,
        "summary": summary,
        "signals": signals,
    }


def save_digital_twin_snapshot(db: Session, patient_id: int):
    payload = digital_twin_payload(db, patient_id)
    snapshot = DigitalTwinSnapshot(
        patient_id=patient_id,
        snapshot_date=date.today(),
        recovery_velocity=payload["recovery_velocity"],
        relapse_probability=payload["relapse_probability"],
        projected_recovery_days=payload["projected_recovery_days"],
        slowdown_risk=payload["slowdown_risk"],
        twin_summary=payload["summary"],
        signals_json=dump_meta(payload["signals"]),
    )
    db.add(snapshot)
    db.flush()
    return snapshot, payload


def habit_insights(db: Session, patient_id: int):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    habits = db.query(HabitEntry).filter(HabitEntry.patient_id == patient_id).order_by(HabitEntry.habit_date.asc()).all()
    habit_by_date = {h.habit_date: h for h in habits}
    matched = [(log, habit_by_date[log.log_date]) for log in logs if log.log_date in habit_by_date]
    if not matched:
        return {"summary": "Add habit entries to discover recovery correlations.", "correlations": []}

    good_sleep_days = [log.pain_score for log, habit in matched if habit.sleep_quality >= 7 or log.sleep_hours >= 7]
    low_sleep_days = [log.pain_score for log, habit in matched if habit.sleep_quality < 7 and log.sleep_hours < 7]
    correlations = []
    if good_sleep_days and low_sleep_days:
        correlations.append(f"Pain averages {round(mean(good_sleep_days), 1)} on good sleep days vs {round(mean(low_sleep_days), 1)} on low sleep days.")
    hydrated = [log.risk_score for log, habit in matched if habit.water_glasses >= 7]
    low_water = [log.risk_score for log, habit in matched if habit.water_glasses < 7]
    if hydrated and low_water:
        correlations.append(f"Risk is lower by {round(mean(low_water) - mean(hydrated), 1)} points on hydrated days.")
    return {"summary": correlations[0] if correlations else "Habits are being tracked; more entries will strengthen insights.", "correlations": correlations}


def journal_ai_payload(text: str):
    emotion = analyze_emotion_text(text)
    stress_score = min(10, emotion["scores"].get("anxiety", 0) * 3 + emotion["scores"].get("fatigue", 0) * 2 + emotion["scores"].get("physical_distress", 0) * 2)
    insight = emotion["support_message"]
    if stress_score >= 6:
        insight = "Stress pattern is rising; the coach should suggest breathing, hydration, and caregiver check-in."
    return {**emotion, "stress_score": stress_score, "insight": insight}


def meal_plan_payload(db: Session, patient_id: int, allergies: str = "", nutrition_goal: str = "balanced recovery"):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    latest = _latest(logs)
    focus = "balanced recovery"
    if latest and latest.fatigue_score >= 6:
        focus = "fatigue support with iron-rich foods and hydration"
    if latest and latest.wound_score >= 6:
        focus = "wound recovery with protein, vitamin C, and zinc"
    if latest and latest.meds_missed_count:
        focus = "gentle meals aligned with medication timing"
    meals = [
        {"time": "Breakfast", "meal": "Oats with banana, nuts, and warm milk", "why": "Slow energy and recovery calories."},
        {"time": "Lunch", "meal": "Dal, rice, spinach, curd, and cucumber", "why": "Protein, iron, hydration, and gut support."},
        {"time": "Snack", "meal": "Fruit bowl with coconut water", "why": "Hydration and micronutrients."},
        {"time": "Dinner", "meal": "Soft roti, paneer or egg curry, and vegetables", "why": "Protein for tissue repair."},
    ]
    if allergies:
        meals.append({"time": "Safety", "meal": f"Avoid: {allergies}", "why": "Allergy-aware recommendation."})
    return {
        "focus": focus,
        "nutrition_goal": nutrition_goal,
        "meals": meals,
        "hydration_plan": "Target 7-9 glasses of water unless restricted by doctor.",
        "ai_reason": f"Plan tuned for {focus}.",
    }


def heatmap_payload(db: Session, patient_id: int):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    cells = []
    for log in logs[-90:]:
        if log.risk_score >= 70:
            state = "severe"
        elif log.risk_score >= 40:
            state = "moderate"
        else:
            state = "good"
        cells.append({"date": str(log.log_date), "state": state, "risk_score": log.risk_score, "pain": log.pain_score})
    return cells


def reward_payload(db: Session, patient_id: int):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    habits = db.query(HabitEntry).filter(HabitEntry.patient_id == patient_id).order_by(HabitEntry.habit_date.asc()).all()
    intakes = db.query(MedicationIntake).filter(MedicationIntake.patient_id == patient_id).all()
    log_dates = {log.log_date for log in logs}
    streak = 0
    cursor = date.today()
    while cursor in log_dates:
        streak += 1
        cursor -= timedelta(days=1)
    xp = streak * 20 + len([h for h in habits if h.water_glasses >= 7]) * 10 + len([m for m in intakes if m.taken]) * 5
    badges = []
    if streak >= 7:
        badges.append("7-Day Recovery Streak")
    if len([m for m in intakes if m.taken]) >= 10:
        badges.append("Medication Consistency")
    if len([h for h in habits if h.water_glasses >= 7]) >= 5:
        badges.append("Hydration Champion")
    if not badges:
        badges.append("Recovery Starter")
    return {"xp": xp, "streak_days": streak, "badges": badges, "next_milestone": "Reach 7 daily logs for the consistency badge."}


def knowledge_payload(db: Session, patient_id: int):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    latest = _latest(logs)
    library = [
        {"title": "Sleep and recovery", "type": "article", "tag": "sleep", "reason": "Sleep improves repair and mood regulation."},
        {"title": "Medication adherence basics", "type": "faq", "tag": "medication", "reason": "Missed doses can increase relapse risk."},
        {"title": "Gentle breathing routine", "type": "video", "tag": "stress", "reason": "Breathing helps reduce stress spikes."},
        {"title": "Post-surgery nutrition", "type": "article", "tag": "nutrition", "reason": "Protein and hydration support recovery."},
    ]
    if latest and latest.sleep_hours < 6:
        preferred = "sleep"
    elif latest and latest.meds_missed_count:
        preferred = "medication"
    elif latest and latest.mood_score <= 2:
        preferred = "stress"
    else:
        preferred = "nutrition"
    return sorted(library, key=lambda item: item["tag"] != preferred)


def health_report_summary(db: Session, patient_id: int):
    score = recovery_score_payload(db, patient_id)
    twin = digital_twin_payload(db, patient_id)
    habit = habit_insights(db, patient_id)
    return (
        f"Patient recovery score is {score['score']}/100 ({score['status']}). "
        f"{twin['summary']} Habit insight: {habit['summary']}"
    )


def coach_payload(db: Session, patient_id: int):
    overview = overview_payload(db, patient_id)
    score = recovery_score_payload(db, patient_id)
    emotion_entries = db.query(HealthJournalEntry).filter(HealthJournalEntry.patient_id == patient_id).order_by(HealthJournalEntry.created_at.asc()).all()
    latest_emotion = _latest(emotion_entries)
    message = "Keep your recovery routine steady today."
    action = "Complete one small recovery habit."
    if overview["prediction"]["risk_level"] == "high":
        message = "Your risk is rising. Reduce strain and check in with caregiver or doctor."
        action = "Repeat symptom check and review medication timing."
    elif latest_emotion and latest_emotion.stress_score >= 6:
        message = "Stress is trending high. Your UI should feel calmer today."
        action = "Try two breathing sessions and write a short journal update."
    elif score["score"] >= 80:
        message = "Great consistency. Protect the streak with hydration, sleep, and medicines."
        action = "Log habits and keep sleep near target."
    return {"message": message, "action": action, "emotion_aware_theme": "calm" if latest_emotion and latest_emotion.stress_score >= 6 else "standard"}


def simulation_payload(db: Session, patient_id: int, sleep_gain=0, adherence_gain=0, exercise_gain=0, stress_reduction=0):
    base = recovery_score_payload(db, patient_id)
    improvement = sleep_gain * 4 + adherence_gain * 0.18 + exercise_gain * 0.08 + stress_reduction * 2.4
    simulated = min(100, round(base["score"] + improvement, 1))
    relapse_drop = min(35, round(improvement * 0.55, 1))
    return {
        "current_score": base["score"],
        "simulated_score": simulated,
        "score_gain": round(simulated - base["score"], 1),
        "estimated_relapse_reduction": relapse_drop,
        "summary": f"If you improve sleep, adherence, activity, and stress as entered, recovery score may improve by {round(simulated - base['score'], 1)} points.",
    }


def adaptive_questions(db: Session, patient_id: int, symptom_hint: str = ""):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    latest = _latest(logs)
    hint = symptom_hint.lower()
    questions = ["How are you feeling compared with yesterday?", "Did you take all medicines on time?"]
    if "head" in hint or (latest and latest.pain_score >= 6):
        questions.extend(["How severe is the headache from 0 to 10?", "How long has it lasted?", "Did you sleep properly?"])
    if "nausea" in hint or "dizzy" in hint:
        questions.extend(["Have you had enough water today?", "Did dizziness happen while standing or resting?"])
    if latest and latest.temperature >= 100.4:
        questions.append("Do you still have fever or chills?")
    return {"questions": questions[:7], "mode": "adaptive", "reason": "Questions adapt to symptom hints and latest daily log."}


def camera_severity_payload(redness=0, swelling=0, discoloration=0, pain_expression=0, image_type="skin"):
    severity = round((redness * 30 + swelling * 30 + discoloration * 20 + pain_expression * 20), 1)
    level = "severe" if severity >= 70 else "moderate" if severity >= 35 else "mild"
    return {
        "image_type": image_type,
        "severity_score": severity,
        "severity_level": level,
        "ai_observation": f"{image_type.title()} severity appears {level}. Track progression and consult doctor if it worsens.",
    }


def extract_prescription(raw_text: str):
    meds = []
    for line in [item.strip() for item in raw_text.splitlines() if item.strip()]:
        lower = line.lower()
        if any(token in lower for token in ["mg", "tablet", "tab", "capsule", "syrup", "daily", "after food", "before food"]):
            meds.append({
                "medicine_name": line.split()[0].strip(":,-"),
                "dosage": next((word for word in line.split() if "mg" in word.lower()), "as prescribed"),
                "timing": "after food" if "after" in lower else "before food" if "before" in lower else "daily",
                "instructions": line,
            })
    if not meds and raw_text.strip():
        meds.append({"medicine_name": raw_text.split()[0], "dosage": "as prescribed", "timing": "daily", "instructions": raw_text[:240]})
    return {"medicines": meds[:8], "confidence": 0.86 if meds else 0.35}


def risk_map_payload(db: Session):
    logs = db.query(DailyLog).all()
    alerts = db.query(Alert).all()
    symptom_counter = Counter()
    risk_by_day = defaultdict(list)
    for log in logs:
        for word in (log.symptom_notes or "").lower().replace(",", " ").split():
            if word in {"pain", "fever", "dizzy", "headache", "fatigue", "swelling", "nausea", "stress"}:
                symptom_counter[word] += 1
        risk_by_day[str(log.log_date)].append(log.risk_score)
    return {
        "common_symptoms": [{"symptom": key, "count": value} for key, value in symptom_counter.most_common(8)],
        "risk_trends": [{"date": key, "avg_risk": round(mean(value), 1)} for key, value in sorted(risk_by_day.items())],
        "alert_distribution": dict(Counter([alert.level for alert in alerts])),
    }


def advanced_hub_payload(db: Session, patient_id: int):
    score_snapshot, score = save_recovery_score_snapshot(db, patient_id)
    twin_snapshot, twin = save_digital_twin_snapshot(db, patient_id)
    goals = db.query(RecoveryGoal).filter(RecoveryGoal.patient_id == patient_id).order_by(RecoveryGoal.created_at.desc()).limit(8).all()
    journals = db.query(HealthJournalEntry).filter(HealthJournalEntry.patient_id == patient_id).order_by(HealthJournalEntry.created_at.desc()).limit(8).all()
    collaboration = db.query(CollaborationItem).filter(CollaborationItem.patient_id == patient_id).order_by(CollaborationItem.created_at.desc()).limit(10).all()
    meals = db.query(MealPlan).filter(MealPlan.patient_id == patient_id).order_by(MealPlan.created_at.desc()).limit(3).all()
    records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).order_by(MedicalRecord.created_at.desc()).limit(6).all()
    scans = db.query(PrescriptionScan).filter(PrescriptionScan.patient_id == patient_id).order_by(PrescriptionScan.created_at.desc()).limit(4).all()
    db.flush()
    return {
        "recovery_score": score,
        "digital_twin": twin,
        "habit_insights": habit_insights(db, patient_id),
        "heatmap": heatmap_payload(db, patient_id),
        "rewards": reward_payload(db, patient_id),
        "knowledge": knowledge_payload(db, patient_id),
        "report_summary": health_report_summary(db, patient_id),
        "coach": coach_payload(db, patient_id),
        "smart_notifications": smart_notification_payload(db, patient_id),
        "sleep_analysis": sleep_analysis_payload(db, patient_id),
        "goals": goals,
        "journals": journals,
        "collaboration": collaboration,
        "meal_plans": [{"id": item.id, "plan_date": item.plan_date, "meals": load_meta(item.meals_json), "hydration_plan": item.hydration_plan, "ai_reason": item.ai_reason} for item in meals],
        "records": records,
        "prescription_scans": [{"id": item.id, "medicines": load_meta(item.extracted_medicines_json), "confidence": item.confidence} for item in scans],
        "snapshot_ids": {"score": score_snapshot.id, "digital_twin": twin_snapshot.id},
    }


def smart_notification_payload(db: Session, patient_id: int):
    adherence = medication_adherence(db, patient_id)
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    latest = _latest(logs)
    messages = []
    if adherence["missed_7d"] >= 3:
        messages.append("You missed medicine 3 or more times this week.")
    if latest and latest.sleep_hours < 6:
        messages.append("Sleep warning: last log is under 6 hours.")
    if latest and latest.temperature >= 100.4:
        messages.append("Fever signal detected. Repeat check and alert caregiver if persistent.")
    if not messages:
        messages.append("No urgent smart notifications right now.")
    return messages


def sleep_analysis_payload(db: Session, patient_id: int):
    logs = db.query(DailyLog).filter(DailyLog.patient_id == patient_id).order_by(DailyLog.log_date.asc()).all()
    if not logs:
        return {"avg_sleep": 0, "quality": "unknown", "correlation": "Need logs for sleep analysis."}
    recent = logs[-14:]
    avg_sleep = round(mean([log.sleep_hours for log in recent]), 1)
    high_sleep = [log.risk_score for log in recent if log.sleep_hours >= 7]
    low_sleep = [log.risk_score for log in recent if log.sleep_hours < 7]
    correlation = "More data needed to compare sleep and symptoms."
    if high_sleep and low_sleep:
        correlation = f"Risk averages {round(mean(high_sleep), 1)} after 7+ hour sleep vs {round(mean(low_sleep), 1)} after shorter sleep."
    return {"avg_sleep": avg_sleep, "quality": "strong" if avg_sleep >= 7 else "needs attention", "correlation": correlation}
