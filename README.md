# RecoverAI - AI-Powered Predictive Recovery Monitoring Platform

RecoverAI has been expanded from symptom logging into a product-style recovery monitoring platform with patient, caregiver, doctor, and admin workflows.

## Major modules added

- AI Recovery Assistant with patient context, risk context, recovery plan context, and urgent-symptom escalation
- Hybrid AI risk engine with explainable factors, wearable signals, medication adherence, camera signals, and predictive alerts
- Wearable/device data module for heart rate, sleep, steps, stress, oxygen saturation, and HRV
- Medication adherence tracking with taken/missed dose history and 7-day adherence score
- Doctor portal for patient review, prescriptions, notes, consultation summaries, and appointments
- Emergency SOS workflow with caregiver, doctor, and admin notifications plus location-ready payloads
- Voice command parsing for symptom-log drafts
- Mood/emotion text analysis for anxiety, fatigue, low mood, and physical distress signals
- Smart recommendation engine for sleep, activity, medication, stress, and clinical escalation
- Recovery timeline with health score trend, streaks, milestones, and improvement tracking
- PDF health reports and CSV export for Excel
- Admin analytics dashboard with risk distribution, recovery success rate, alert frequency, audit logs, and wearable sample count
- PWA manifest, offline app shell cache, dark mode, large text toggle, and reduced-motion accessibility support
- JWT-style access tokens, refresh tokens, audit logs, and provider-status notification records
- Advanced Recovery Hub with digital twin profile, AI recovery score, recovery heatmap, smart habits, health journal, collaboration space, AI meal planner, smart goals, community support, secure medical vault, OCR prescription scanner, adaptive check-in, camera severity demo, recovery simulation, AI coach, knowledge recommendations, smart notifications, sleep analysis, WebSocket-ready live monitoring, and multi-language readiness for English/Hindi/Marathi
- Admin AI health risk map for symptom clusters, risk trends, and alert distribution

## API modules

- `/api/assistant`
- `/api/intelligence`
- `/api/doctors`
- `/api/reports`
- `/api/advanced`
- `/api/auth`
- `/api/patients`
- `/api/caregivers`
- `/api/admin`
- `/api/notifications`
- `/api/risk`

## External service notes

The project is integration-ready for OpenAI/Gemini, Google Fit, Apple Health, Fitbit, Twilio, Firebase Cloud Messaging, and WhatsApp providers. In this build, those flows run in deterministic local/dev mode so the app works without paid keys.

Real OTP email sending works after SMTP variables are configured. OTP codes are no longer returned to the browser. If SMTP is not configured, registration/password reset will ask you to configure email instead of showing a demo OTP.

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_USE_TLS=true`

For a local-only demo, you can temporarily set `DEV_SHOW_OTP=true` to print OTP emails in the backend terminal. Do not use that setting for submission or production.

### OTP email setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Fill your SMTP details. For Gmail, enable 2-Step Verification and create a Gmail App Password.
3. Keep `DEV_SHOW_OTP=false` when you want real email delivery.
4. Restart the backend after changing `.env`.

Example Gmail values:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM=your_email@gmail.com
SMTP_USE_TLS=true
DEV_SHOW_OTP=false
```

Database:

- Default: SQLite database at `backend/recoverai.db`
- Optional: set `DATABASE_URL` to another SQLAlchemy connection string

Security token settings:

- `JWT_SECRET`
- `ACCESS_TOKEN_MINUTES`
- `REFRESH_TOKEN_DAYS`

## Run from scratch

### Backend

```powershell
cd recoverai_authfix\backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd recoverai_authfix\frontend
npm install
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- Backend docs: `http://127.0.0.1:8000/docs`

## Demo flow

1. Register a caregiver, doctor, admin, and patient.
2. Login as patient and complete onboarding with caregiver and doctor assignment.
3. Submit daily logs and optional wearable samples.
4. Open AI Health Center for assistant chat, relapse prediction, XAI, medication adherence, SOS, reports, voice, and mood tools.
5. Login as caregiver to see linked patients and emergency alerts.
6. Login as doctor to add notes, prescriptions, and appointments.
7. Login as admin to see analytics, alerts, notifications, and system KPIs.
