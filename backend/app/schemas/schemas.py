from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class OTPRequestPayload(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str
    phone: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"patient", "caregiver", "doctor", "admin"}:
            raise ValueError("Role must be patient, caregiver, doctor, or admin")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None


class OTPVerifyPayload(OTPRequestPayload):
    otp_code: str = Field(..., min_length=4, max_length=6)

    @field_validator("otp_code")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("OTP must contain only digits")
        return value


class OTPEmailOnlyPayload(BaseModel):
    email: EmailStr


class PasswordResetPayload(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("otp_code")
    @classmethod
    def validate_reset_otp(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("OTP must contain only digits")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PatientOnboarding(BaseModel):
    age: int = Field(..., ge=1, le=120)
    gender: str
    diagnosis: str
    surgery_type: Optional[str] = None
    discharge_date: date
    comorbidities: List[str] = Field(default_factory=list)
    caregiver_id: Optional[int] = None
    doctor_id: Optional[int] = None
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    location_consent: bool = False
    health_goal: str = ""
    preferred_language: str = "English"
    accessibility_mode: str = "standard"
    notes: str = ""
    target_sleep_hours: float = 8.0
    target_steps: int = 2500
    reminder_time: str = "20:00"
    medications: List[dict] = Field(default_factory=list)


class DailyLogCreate(BaseModel):
    log_date: date
    pain_score: int = Field(..., ge=0, le=10)
    temperature: float = Field(..., ge=95, le=107)
    mood_score: int = Field(..., ge=1, le=5)
    mobility_score: int = Field(..., ge=1, le=5)
    sleep_hours: float = Field(..., ge=0, le=24)
    meds_taken: bool
    meds_missed_count: int = Field(0, ge=0, le=10)
    symptom_notes: str = ""
    engagement_minutes: int = Field(0, ge=0, le=1440)
    fatigue_score: int = Field(0, ge=0, le=10)
    swelling_score: int = Field(0, ge=0, le=10)
    wound_score: int = Field(0, ge=0, le=10)
    voice_note: str = ""


class CameraScanPayload(BaseModel):
    redness_index: float = Field(..., ge=0, le=1)
    swelling_index: float = Field(..., ge=0, le=1)
    fatigue_index: float = Field(..., ge=0, le=1)
    pain_face_index: float = Field(..., ge=0, le=1)
    skin_tone_index: float = Field(..., ge=0, le=1)


class AlertAckPayload(BaseModel):
    alert_id: int


class NotificationReadPayload(BaseModel):
    notification_id: int


class AssistantChatPayload(BaseModel):
    user_id: Optional[int] = None
    message: str = Field(..., min_length=2, max_length=1200)


class WearableMetricPayload(BaseModel):
    source: str = "manual"
    metric_date: date
    heart_rate: int = Field(0, ge=0, le=240)
    sleep_hours: float = Field(0, ge=0, le=24)
    steps: int = Field(0, ge=0, le=100000)
    stress_level: int = Field(0, ge=0, le=10)
    oxygen_saturation: float = Field(0, ge=0, le=100)
    hrv_score: float = Field(0, ge=0, le=250)


class MedicationIntakePayload(BaseModel):
    schedule_id: Optional[int] = None
    intake_date: date
    medicine_name: str = Field(..., min_length=1, max_length=120)
    taken: bool = True
    notes: str = ""


class DoctorNotePayload(BaseModel):
    patient_id: int
    note_type: str = "consultation"
    summary: str = Field(..., min_length=3, max_length=3000)
    prescription: str = ""
    follow_up_date: Optional[date] = None


class AppointmentPayload(BaseModel):
    patient_id: int
    scheduled_at: datetime
    reason: str = ""
    notes: str = ""


class EmergencyPayload(BaseModel):
    triggered_by_user_id: Optional[int] = None
    severity: str = "critical"
    message: str = "Emergency support requested from RecoverAI."
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str = ""


class VoiceCommandPayload(BaseModel):
    transcript: str = Field(..., min_length=2, max_length=1200)


class EmotionPayload(BaseModel):
    text: str = Field(..., min_length=2, max_length=2000)


class RefreshTokenPayload(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class HabitEntryPayload(BaseModel):
    habit_date: date
    water_glasses: int = Field(0, ge=0, le=40)
    meditation_minutes: int = Field(0, ge=0, le=300)
    exercise_minutes: int = Field(0, ge=0, le=300)
    breathing_sessions: int = Field(0, ge=0, le=30)
    screen_time_hours: float = Field(0, ge=0, le=24)
    sleep_quality: int = Field(0, ge=0, le=10)


class JournalEntryPayload(BaseModel):
    user_id: Optional[int] = None
    journal_date: date
    text: str = Field(..., min_length=3, max_length=4000)


class CollaborationPayload(BaseModel):
    created_by_user_id: Optional[int] = None
    item_type: str = "note"
    title: str = Field(..., min_length=2, max_length=160)
    body: str = ""
    assigned_to_user_id: Optional[int] = None
    due_date: Optional[date] = None
    status: str = "open"


class MealPlanPayload(BaseModel):
    plan_date: date
    allergies: str = ""
    nutrition_goal: str = "balanced recovery"


class GoalPayload(BaseModel):
    goal_type: str = Field(..., min_length=2, max_length=80)
    target_value: float = 0
    unit: str = ""
    current_value: float = 0


class CommunityThreadPayload(BaseModel):
    patient_id: Optional[int] = None
    user_id: Optional[int] = None
    group_name: str = "Recovery Circle"
    title: str = Field(..., min_length=3, max_length=160)
    body: str = ""
    anonymous: bool = True


class CommunityPostPayload(BaseModel):
    user_id: Optional[int] = None
    body: str = Field(..., min_length=2, max_length=3000)


class MedicalRecordPayload(BaseModel):
    uploaded_by_user_id: Optional[int] = None
    record_type: str = "report"
    file_name: str = ""
    content_text: str = ""


class PrescriptionScanPayload(BaseModel):
    raw_text: str = Field(..., min_length=3, max_length=5000)
    auto_add_medications: bool = True


class SimulationPayload(BaseModel):
    sleep_gain_hours: float = Field(0, ge=0, le=6)
    medication_adherence_gain: float = Field(0, ge=0, le=100)
    exercise_gain_minutes: int = Field(0, ge=0, le=180)
    stress_reduction: int = Field(0, ge=0, le=10)


class AdaptiveCheckinPayload(BaseModel):
    symptom_hint: str = ""


class CameraSeverityPayload(BaseModel):
    image_type: str = "skin"
    redness_index: float = Field(0, ge=0, le=1)
    swelling_index: float = Field(0, ge=0, le=1)
    discoloration_index: float = Field(0, ge=0, le=1)
    pain_expression_index: float = Field(0, ge=0, le=1)
