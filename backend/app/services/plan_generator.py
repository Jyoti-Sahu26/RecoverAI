from typing import Any, Dict, List, Optional


def generate_profile(
    age: int,
    diagnosis: str,
    surgery_type: Optional[str],
    comorbidities: List[str],
) -> Dict[str, str]:
    diagnosis_lower = (diagnosis or "").lower()
    surgery_lower = (surgery_type or "").lower()
    comorbidities = comorbidities or []

    recovery_type = "guided"
    monitoring_level = "standard"
    baseline_risk = "moderate"

    if age >= 65 or len(comorbidities) >= 2:
        monitoring_level = "intensive"
        baseline_risk = "high"

    if any(term in diagnosis_lower for term in ["cardiac", "joint", "orthopedic", "fracture", "knee", "hip"]):
        recovery_type = "mobility-focused"
    elif any(term in diagnosis_lower for term in ["wound", "infection", "healing", "skin"]):
        recovery_type = "healing-focused"
    elif any(term in surgery_lower for term in ["surgery", "post-op", "operation"]):
        recovery_type = "post-operative"

    return {
        "recovery_type": recovery_type,
        "monitoring_level": monitoring_level,
        "baseline_risk": baseline_risk,
    }


def generate_recovery_plan(payload: Any, profile: Dict[str, str]) -> Dict[str, Any]:
    tasks = [
        "Take medicines on time and confirm in the app.",
        "Submit one daily symptom log every day.",
        "Hydrate well and follow discharge instructions.",
    ]
    precautions = [
        "Seek urgent care for severe pain, high fever, or breathing difficulty.",
        "Avoid overexertion during early recovery.",
    ]

    target_steps = getattr(payload, "target_steps", 3000)
    target_sleep_hours = getattr(payload, "target_sleep_hours", 7)
    diagnosis = getattr(payload, "diagnosis", "recovery case")

    if profile.get("recovery_type") == "mobility-focused":
        tasks.extend([
            f"Walk progressively toward {target_steps} daily steps.",
            "Complete gentle mobility exercises twice a day.",
        ])
    elif profile.get("recovery_type") == "healing-focused":
        tasks.extend([
            "Track swelling and wound condition using the daily scan section.",
            "Keep wound photos consistent if advised by your clinician.",
        ])
        precautions.append("Keep wound area clean and dry unless advised otherwise.")
    elif profile.get("recovery_type") == "post-operative":
        tasks.append("Follow post-operative precautions and rest cycles carefully.")

    if target_sleep_hours >= 7:
        tasks.append(f"Aim for about {target_sleep_hours} hours of sleep.")

    summary = (
        f"{profile.get('recovery_type', 'guided').replace('-', ' ').title()} plan with "
        f"{profile.get('monitoring_level', 'standard')} monitoring for {diagnosis}."
    )

    return {
        "phase": "stabilization",
        "summary": summary,
        "daily_tasks": tasks,
        "precautions": precautions,
        "reminder_frequency": "high" if profile.get("monitoring_level") == "intensive" else "normal",
    }
