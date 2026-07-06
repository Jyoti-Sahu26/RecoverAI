def analyze_camera_scan(scan):
    hints = []
    if getattr(scan, "skin_tone_index", 0) < 0.25:
        hints.append("Skin tone variation suggests checking oxygen or anemia indicators.")
    if getattr(scan, "redness_index", 0) > 0.6:
        hints.append("Redness appears elevated; monitor for inflammation.")
    if getattr(scan, "swelling_index", 0) > 0.6:
        hints.append("Swelling trend appears elevated.")
    if getattr(scan, "fatigue_index", 0) > 0.6:
        hints.append("Face-based fatigue signal appears high.")
    if getattr(scan, "pain_face_index", 0) > 0.6:
        hints.append("Pain expression indicator appears high.")

    return {
        "hints": hints or ["No strong visual concern detected from this prototype scan."],
    }
