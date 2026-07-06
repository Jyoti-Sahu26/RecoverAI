from statistics import mean


def classify_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def _build_recommendations(level, latest, pain_avg, temp_avg):
    common = [
        "Continue daily logging without missing a day.",
        "Stay hydrated and follow medicine timing carefully.",
    ]
    if level in {"high", "critical"}:
        return {
            "common": common + [
                "Contact caregiver immediately.",
                "Consider clinical review if symptoms persist or worsen.",
                "Increase monitoring frequency for the next 24 hours.",
            ],
            "personalized": [
                f"Current pain score is {latest.pain_score}; reduce strain and reassess in 4 to 6 hours.",
                f"Recent average temperature is {round(temp_avg, 1)} F; monitor fever closely.",
                "If swelling or wound scores remain high, request wound review.",
            ],
        }
    if level == "moderate":
        return {
            "common": common + [
                "Repeat symptom check later today.",
                "Improve medication adherence and rest quality.",
            ],
            "personalized": [
                f"Recent pain average is {round(pain_avg, 1)}; use recovery plan tasks consistently.",
                "Complete wearable sync or camera scan for more personalized recommendations.",
            ],
        }
    return {
        "common": common + ["Continue current recovery plan."],
        "personalized": ["For more personalized suggestions, keep entering sleep, activity, wearable, and scan data."],
    }


def _trend_delta(items, attr):
    if len(items) < 2:
        return 0
    return getattr(items[-1], attr, 0) - getattr(items[0], attr, 0)


def calculate_patient_risk(patient, logs, camera_scan=None, wearable_metrics=None, adherence=None):
    if not patient or not logs:
        return {
            "risk_score": 0,
            "risk_level": "unknown",
            "explanation": ["No patient or log data available."],
            "recommendations_common": ["Complete onboarding and submit daily logs."],
            "recommendations_personalized": ["Add symptoms, wearable data, and camera inputs for tailored guidance."],
            "recommendation_mode": "common",
            "summary": {},
            "xai_factors": [],
            "model_version": "RecoverAI hybrid clinical ML v2",
        }

    last = logs[-1]
    recent = logs[-5:]
    wearables = (wearable_metrics or [])[-5:]
    adherence = adherence or {}
    score = 0
    reasons = []
    xai_factors = []

    def add(points, feature, reason):
        nonlocal score
        if points <= 0:
            return
        score += points
        reasons.append(reason)
        xai_factors.append({"feature": feature, "impact": round(points, 2), "reason": reason})

    if last.pain_score >= 8:
        add(20, "pain_score", "Pain is very high.")
    elif last.pain_score >= 6:
        add(10, "pain_score", "Pain is elevated.")

    if last.temperature >= 100.4:
        add(20, "temperature", "Temperature suggests possible fever.")

    if last.mobility_score <= 2:
        add(10, "mobility_score", "Mobility is low.")

    if not last.meds_taken:
        add(15, "medication_taken", "Medication was not taken today.")

    if last.meds_missed_count >= 2:
        add(10, "missed_doses", "Multiple medication doses were missed.")

    if last.mood_score <= 2:
        add(8, "mood_score", "Mood indicates a low emotional state.")

    if last.engagement_minutes < 2:
        add(8, "engagement", "App engagement is very low.")

    if last.fatigue_score >= 7:
        add(10, "fatigue_score", "Fatigue score is high.")

    if last.swelling_score >= 7:
        add(10, "swelling_score", "Swelling report is concerning.")

    if last.wound_score >= 7:
        add(12, "wound_score", "Wound healing concern was reported.")

    pain_avg = mean([x.pain_score for x in recent])
    temp_avg = mean([x.temperature for x in recent])

    if _trend_delta(recent, "pain_score") > 0:
        add(10, "pain_trend", "Pain trend is worsening over recent logs.")

    if _trend_delta(recent, "temperature") > 0:
        add(8, "temperature_trend", "Temperature trend is increasing.")

    if _trend_delta(recent, "mobility_score") < 0:
        add(8, "mobility_trend", "Mobility trend is declining.")

    target_sleep = getattr(patient, "target_sleep_hours", 8) or 8
    sleep_avg = mean([x.sleep_hours for x in recent])
    if sleep_avg < target_sleep - 1:
        add(9, "sleep_gap", "Sleep is below the personalized recovery target.")

    if patient.age >= 60:
        add(5, "age", "Age places the patient in a higher monitoring category.")

    comorbidity_count = len([x for x in (patient.comorbidities or "").split(",") if x.strip()])
    if comorbidity_count >= 2:
        add(6, "comorbidities", "Multiple comorbidities raise recovery complexity.")

    if patient.monitoring_level == "intensive":
        add(5, "monitoring_level", "Patient is tagged for intensive monitoring.")

    adherence_score = adherence.get("adherence_score")
    if adherence_score is not None and adherence_score < 75:
        add(14, "medication_adherence", "Medication adherence is below 75%.")
    elif adherence_score is not None and adherence_score < 90:
        add(6, "medication_adherence", "Medication adherence needs improvement.")

    wearable_summary = {}
    if wearables:
        stress_avg = mean([item.stress_level for item in wearables])
        wearable_sleep_avg = mean([item.sleep_hours for item in wearables])
        steps_avg = mean([item.steps for item in wearables])
        spo2_values = [item.oxygen_saturation for item in wearables if item.oxygen_saturation]
        wearable_summary = {
            "avg_stress": round(stress_avg, 2),
            "avg_sleep": round(wearable_sleep_avg, 2),
            "avg_steps": round(steps_avg, 2),
            "avg_spo2": round(mean(spo2_values), 2) if spo2_values else 0,
        }
        if stress_avg >= 7:
            add(10, "wearable_stress", "Wearable stress trend is elevated.")
        if wearable_sleep_avg < 6:
            add(9, "wearable_sleep", "Wearable sleep duration is low.")
        if steps_avg < max(800, getattr(patient, "target_steps", 2500) * 0.35):
            add(6, "wearable_steps", "Wearable activity is far below target.")
        if spo2_values and mean(spo2_values) < 94:
            add(12, "oxygen_saturation", "Oxygen saturation is below the preferred recovery range.")

    camera_hints = []
    if camera_scan:
        redness = int(getattr(camera_scan, "redness_index", 0) * 15)
        swelling = int(getattr(camera_scan, "swelling_index", 0) * 15)
        fatigue = int(getattr(camera_scan, "fatigue_index", 0) * 10)
        pain_face = int(getattr(camera_scan, "pain_face_index", 0) * 12)
        add(redness, "camera_redness", "Camera scan indicates redness.")
        add(swelling, "camera_swelling", "Camera scan indicates swelling.")
        add(fatigue, "camera_fatigue", "Camera scan indicates visible fatigue.")
        add(pain_face, "camera_pain", "Camera scan indicates pain expression.")
        if getattr(camera_scan, "hints", ""):
            camera_hints = [x.strip() for x in camera_scan.hints.split("||") if x.strip()]
            for hint in camera_hints[:2]:
                if hint not in reasons:
                    reasons.append(hint)

    level = classify_level(score)
    recommendations = _build_recommendations(level, last, pain_avg, temp_avg)
    mode = "hybrid" if wearables or camera_scan or adherence else "common"
    xai_factors.sort(key=lambda item: item["impact"], reverse=True)

    trend_score = 0
    if _trend_delta(recent, "pain_score") > 0:
        trend_score += 1
    if _trend_delta(recent, "mobility_score") < 0:
        trend_score += 1
    if sleep_avg < target_sleep - 1:
        trend_score += 1
    predictive_alert = {
        "active": level in {"high", "critical"} or trend_score >= 2,
        "message": "You may enter a higher-risk state within 2 days if these trends continue." if trend_score >= 2 else "No near-term worsening pattern detected.",
        "horizon_days": 2,
    }

    return {
        "risk_score": round(score, 2),
        "risk_level": level,
        "explanation": reasons or ["Stable recovery trend from current inputs."],
        "recommendations_common": recommendations["common"],
        "recommendations_personalized": recommendations["personalized"],
        "recommendation_mode": mode,
        "summary": {
            "pain_avg_recent": round(pain_avg, 2),
            "temp_avg_recent": round(temp_avg, 2),
            "sleep_avg_recent": round(sleep_avg, 2),
            "camera_hints": camera_hints,
            "wearable_summary": wearable_summary,
            "adherence_score": adherence_score,
        },
        "xai_factors": xai_factors[:8],
        "predictive_alert": predictive_alert,
        "model_version": "RecoverAI hybrid clinical ML v2",
    }
