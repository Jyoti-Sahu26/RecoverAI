from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    otp_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OTPRequest(Base):
    __tablename__ = "otp_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    purpose = Column(String, default="register")
    meta_json = Column(Text, default="")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    diagnosis = Column(String, nullable=False)
    surgery_type = Column(String, nullable=True)
    discharge_date = Column(Date, nullable=False)
    comorbidities = Column(Text, default="")
    baseline_risk = Column(String, default="moderate")
    caregiver_id = Column(Integer, nullable=True)
    doctor_id = Column(Integer, nullable=True)
    emergency_contact_name = Column(String, default="")
    emergency_contact_phone = Column(String, default="")
    location_consent = Column(Boolean, default=False)
    health_goal = Column(Text, default="")
    preferred_language = Column(String, default="English")
    accessibility_mode = Column(String, default="standard")
    onboarding_completed = Column(Boolean, default=False)
    monitoring_level = Column(String, default="standard")
    recovery_type = Column(String, default="guided")
    target_sleep_hours = Column(Float, default=8.0)
    target_steps = Column(Integer, default=2500)
    notes = Column(Text, default="")
    reminder_time = Column(String, default="20:00")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), unique=True)
    phase = Column(String, default="stabilization")
    summary = Column(Text, nullable=False)
    daily_tasks = Column(Text, default="")
    precautions = Column(Text, default="")
    reminder_frequency = Column(String, default="normal")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medicine_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    timing = Column(String, nullable=False)
    instructions = Column(Text, default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MedicationIntake(Base):
    __tablename__ = "medication_intakes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    schedule_id = Column(Integer, ForeignKey("medication_schedules.id"), nullable=True)
    intake_date = Column(Date, nullable=False)
    medicine_name = Column(String, nullable=False)
    taken = Column(Boolean, default=True)
    taken_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    log_date = Column(Date, nullable=False)
    pain_score = Column(Integer, nullable=False)
    temperature = Column(Float, nullable=False)
    mood_score = Column(Integer, nullable=False)
    mobility_score = Column(Integer, nullable=False)
    sleep_hours = Column(Float, nullable=False)
    meds_taken = Column(Boolean, default=True)
    meds_missed_count = Column(Integer, default=0)
    symptom_notes = Column(Text, default="")
    engagement_minutes = Column(Integer, default=0)
    fatigue_score = Column(Integer, default=0)
    swelling_score = Column(Integer, default=0)
    wound_score = Column(Integer, default=0)
    voice_note = Column(Text, default="")
    risk_score = Column(Float, default=0)
    risk_level = Column(String, default="unknown")
    risk_explanation = Column(Text, default="")
    risk_recommendations = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    recipient_user_id = Column(Integer, nullable=True)
    level = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    target_role = Column(String, default="caregiver")
    status = Column(String, default="open")
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CameraScan(Base):
    __tablename__ = "camera_scans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    skin_tone_index = Column(Float, default=0)
    redness_index = Column(Float, default=0)
    swelling_index = Column(Float, default=0)
    fatigue_index = Column(Float, default=0)
    pain_face_index = Column(Float, default=0)
    hints = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    kind = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String, default="in_app")
    email_to = Column(String, nullable=True)
    sent = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    provider_status = Column(String, default="queued")
    external_reference = Column(String, default="")
    related_alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)


class WearableMetric(Base):
    __tablename__ = "wearable_metrics"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    source = Column(String, default="manual")
    metric_date = Column(Date, nullable=False)
    heart_rate = Column(Integer, default=0)
    sleep_hours = Column(Float, default=0)
    steps = Column(Integer, default=0)
    stress_level = Column(Integer, default=0)
    oxygen_saturation = Column(Float, default=0)
    hrv_score = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sender = Column(String, default="patient")
    message = Column(Text, nullable=False)
    response = Column(Text, default="")
    context_json = Column(Text, default="")
    safety_level = Column(String, default="standard")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DoctorNote(Base):
    __tablename__ = "doctor_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_user_id = Column(Integer, ForeignKey("users.id"))
    note_type = Column(String, default="consultation")
    summary = Column(Text, nullable=False)
    prescription = Column(Text, default="")
    follow_up_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_user_id = Column(Integer, ForeignKey("users.id"))
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, default="")
    status = Column(String, default="scheduled")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    severity = Column(String, default="critical")
    message = Column(Text, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, default="")
    status = Column(String, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=True)
    metadata_json = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    refresh_token_hash = Column(String, nullable=False, index=True)
    user_agent = Column(String, default="")
    revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecoveryScoreSnapshot(Base):
    __tablename__ = "recovery_score_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    score_date = Column(Date, nullable=False)
    score = Column(Float, default=0)
    status = Column(String, default="unknown")
    components_json = Column(Text, default="")
    insights = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DigitalTwinSnapshot(Base):
    __tablename__ = "digital_twin_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    snapshot_date = Column(Date, nullable=False)
    recovery_velocity = Column(Float, default=0)
    relapse_probability = Column(Float, default=0)
    projected_recovery_days = Column(Integer, default=0)
    slowdown_risk = Column(Float, default=0)
    twin_summary = Column(Text, default="")
    signals_json = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HabitEntry(Base):
    __tablename__ = "habit_entries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    habit_date = Column(Date, nullable=False)
    water_glasses = Column(Integer, default=0)
    meditation_minutes = Column(Integer, default=0)
    exercise_minutes = Column(Integer, default=0)
    breathing_sessions = Column(Integer, default=0)
    screen_time_hours = Column(Float, default=0)
    sleep_quality = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HealthJournalEntry(Base):
    __tablename__ = "health_journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    journal_date = Column(Date, nullable=False)
    text = Column(Text, nullable=False)
    sentiment = Column(String, default="neutral")
    emotion = Column(String, default="stable")
    stress_score = Column(Float, default=0)
    ai_insight = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CollaborationItem(Base):
    __tablename__ = "collaboration_items"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    item_type = Column(String, default="note")
    title = Column(String, default="")
    body = Column(Text, default="")
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    plan_date = Column(Date, nullable=False)
    allergies = Column(Text, default="")
    nutrition_goal = Column(String, default="balanced recovery")
    meals_json = Column(Text, default="")
    hydration_plan = Column(Text, default="")
    ai_reason = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecoveryGoal(Base):
    __tablename__ = "recovery_goals"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    goal_type = Column(String, nullable=False)
    target_value = Column(Float, default=0)
    unit = Column(String, default="")
    current_value = Column(Float, default=0)
    status = Column(String, default="active")
    ai_tip = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CommunityThread(Base):
    __tablename__ = "community_threads"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    group_name = Column(String, default="Recovery Circle")
    title = Column(String, nullable=False)
    body = Column(Text, default="")
    anonymous = Column(Boolean, default=True)
    ai_moderation = Column(String, default="approved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("community_threads.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    body = Column(Text, nullable=False)
    ai_moderation = Column(String, default="approved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    record_type = Column(String, default="report")
    file_name = Column(String, default="")
    content_text = Column(Text, default="")
    encrypted_reference = Column(String, default="")
    ocr_text = Column(Text, default="")
    ai_summary = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PrescriptionScan(Base):
    __tablename__ = "prescription_scans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    raw_text = Column(Text, default="")
    extracted_medicines_json = Column(Text, default="")
    confidence = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
