import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AlertBadge from "../components/AlertBadge";
import Navbar from "../components/Navbar";
import SectionCard from "../components/SectionCard";
import StatCard from "../components/StatCard";
import api from "../services/api";

const today = () => new Date().toISOString().split("T")[0];

export default function AIHealthCenter() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [overview, setOverview] = useState(null);
  const [wearables, setWearables] = useState([]);
  const [adherence, setAdherence] = useState(null);
  const [chatInput, setChatInput] = useState("");
  const [chat, setChat] = useState([]);
  const [voiceText, setVoiceText] = useState("Log headache and dizziness with mild pain");
  const [voiceDraft, setVoiceDraft] = useState(null);
  const [emotionText, setEmotionText] = useState("I feel tired and worried about my recovery today.");
  const [emotion, setEmotion] = useState(null);
  const [message, setMessage] = useState("");
  const [wearableForm, setWearableForm] = useState({
    source: "manual",
    metric_date: today(),
    heart_rate: 78,
    sleep_hours: 6.5,
    steps: 2600,
    stress_level: 5,
    oxygen_saturation: 97,
    hrv_score: 52,
  });

  const load = async () => {
    try {
      const profileRes = await api.get(`/patients/profile/by-user/${user.user_id}`);
      if (!profileRes.data.patient) {
        navigate("/onboarding");
        return;
      }
      const activePatient = profileRes.data.patient;
      setPatient(activePatient);
      const [dashboardRes, overviewRes, wearableRes, adherenceRes, chatRes] = await Promise.all([
        api.get(`/patients/by-user/${user.user_id}/dashboard`),
        api.get(`/intelligence/patients/${activePatient.id}/overview`),
        api.get(`/intelligence/patients/${activePatient.id}/wearables`),
        api.get(`/intelligence/patients/${activePatient.id}/medications/adherence`),
        api.get(`/assistant/patient/${activePatient.id}/history`),
      ]);
      setDashboard(dashboardRes.data);
      setOverview(overviewRes.data);
      setWearables(wearableRes.data || []);
      setAdherence(adherenceRes.data);
      setChat((chatRes.data || []).reverse());
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load AI health center");
    }
  };

  useEffect(() => {
    if (user?.user_id) load();
  }, [user?.user_id]);

  const reportUrl = (type) => `${api.defaults.baseURL}/reports/patient/${patient?.id}/${type}`;

  const sendChat = async () => {
    if (!patient || !chatInput.trim()) return;
    try {
      const res = await api.post(`/assistant/patient/${patient.id}/chat`, { user_id: user.user_id, message: chatInput.trim() });
      setChat((prev) => [...prev, { id: Date.now(), message: chatInput.trim(), response: res.data.reply, safety_level: res.data.safety_level }]);
      setChatInput("");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Assistant failed to respond");
    }
  };

  const syncWearable = async (demo = false) => {
    if (!patient) return;
    try {
      const payload = {
        ...wearableForm,
        heart_rate: Number(wearableForm.heart_rate),
        sleep_hours: Number(wearableForm.sleep_hours),
        steps: Number(wearableForm.steps),
        stress_level: Number(wearableForm.stress_level),
        oxygen_saturation: Number(wearableForm.oxygen_saturation),
        hrv_score: Number(wearableForm.hrv_score),
      };
      if (demo) {
        await api.post(`/intelligence/patients/${patient.id}/wearables/sync-demo`);
      } else {
        await api.post(`/intelligence/patients/${patient.id}/wearables`, payload);
      }
      await load();
      setMessage("Wearable data synced and prediction refreshed.");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to sync wearable data");
    }
  };

  const markMedication = async (med, taken) => {
    if (!patient) return;
    try {
      await api.post(`/intelligence/patients/${patient.id}/medications/intake`, {
        schedule_id: med.id,
        intake_date: today(),
        medicine_name: med.medicine_name,
        taken,
        notes: taken ? "Marked from AI Health Center" : "Missed dose alert",
      });
      await load();
      setMessage(taken ? "Medicine marked as taken." : "Missed dose recorded.");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to update medicine");
    }
  };

  const parseVoice = async () => {
    if (!patient) return;
    try {
      const res = await api.post(`/intelligence/patients/${patient.id}/voice-command`, { transcript: voiceText });
      setVoiceDraft(res.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Voice command parsing failed");
    }
  };

  const analyzeEmotion = async () => {
    if (!patient) return;
    try {
      const res = await api.post(`/intelligence/patients/${patient.id}/emotion`, { text: emotionText });
      setEmotion(res.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Emotion analysis failed");
    }
  };

  const triggerSos = async () => {
    if (!patient) return;
    const submit = async (coords = {}) => {
      const res = await api.post(`/intelligence/patients/${patient.id}/emergency`, {
        triggered_by_user_id: user.user_id,
        severity: "critical",
        message: "Patient triggered emergency SOS from RecoverAI.",
        latitude: coords.latitude,
        longitude: coords.longitude,
        address: "",
      });
      setMessage(`SOS triggered. Notified ${res.data.notified_users.length} emergency contacts.`);
    };

    if (navigator.geolocation && patient.location_consent) {
      navigator.geolocation.getCurrentPosition(
        (position) => submit(position.coords),
        () => submit(),
        { timeout: 5000 },
      );
    } else {
      await submit();
    }
  };

  const timeline = overview?.timeline?.points || [];
  const wearableChart = useMemo(() => wearables.map((item) => ({
    date: item.metric_date,
    sleep: item.sleep_hours,
    stress: item.stress_level,
    steps: Math.round((item.steps || 0) / 1000),
    spo2: item.oxygen_saturation,
  })), [wearables]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#e0f2fe,_#f8fafc_42%,_#dcfce7_100%)] p-4">
      <div className="mx-auto max-w-7xl space-y-4">
        <Navbar title="AI Health Center" />
        {message ? <div className="rounded-2xl bg-slate-100 p-3 text-sm text-slate-700">{message}</div> : null}

        <div className="grid gap-4 md:grid-cols-4">
          <StatCard label="Relapse probability" value={`${overview?.prediction?.probability ?? 0}%`} hint={overview?.prediction?.trend || "Prediction activates after logs"} />
          <StatCard label="Adherence" value={`${overview?.adherence?.adherence_score ?? 0}%`} hint={overview?.adherence?.status || "Medication tracking"} />
          <StatCard label="Wearable source" value={overview?.wearable_summary?.source || "None"} hint={overview?.wearable_summary?.trend || "Sync device data"} />
          <StatCard label="Streak" value={`${overview?.timeline?.streak_days ?? 0} days`} hint="Daily recovery consistency" />
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <div className="space-y-4 xl:col-span-2">
            <SectionCard title="AI recovery assistant" subtitle="Answers with patient history, risk, recovery plan, and safety escalation.">
              <div className="h-80 space-y-3 overflow-y-auto rounded-2xl bg-slate-50 p-3">
                {chat.length === 0 ? <p className="text-sm text-slate-500">Ask about symptoms, food, exercise, medicine, or risk.</p> : chat.map((item) => (
                  <div key={item.id} className="rounded-2xl bg-white p-3 text-sm shadow-sm">
                    <p className="font-semibold text-slate-900">You</p>
                    <p className="text-slate-700">{item.message}</p>
                    <p className="mt-2 font-semibold text-emerald-700">RecoverAI Assistant</p>
                    <p className="text-slate-700">{item.response}</p>
                    {item.safety_level === "urgent" ? <p className="mt-2 text-rose-700">Urgent safety guidance detected.</p> : null}
                  </div>
                ))}
              </div>
              <div className="mt-3 flex flex-col gap-2 md:flex-row">
                <input className="min-w-0 flex-1 rounded-2xl border border-slate-200 p-3" placeholder="Ask RecoverAI..." value={chatInput} onChange={(e) => setChatInput(e.target.value)} />
                <button onClick={sendChat} className="rounded-2xl bg-slate-900 px-5 py-3 text-white">Send</button>
              </div>
            </SectionCard>

            <SectionCard title="Predictive relapse detection and explainable AI" subtitle="Hybrid scoring combines symptoms, medication, wearable trends, and camera signals.">
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-900">Current risk</p>
                    <AlertBadge level={overview?.risk?.risk_level} />
                  </div>
                  <p className="mt-3 text-4xl font-bold text-slate-900">{overview?.risk?.risk_score ?? 0}</p>
                  <p className="mt-2 text-sm text-slate-600">{overview?.risk?.predictive_alert?.message}</p>
                  <div className="mt-4 rounded-xl bg-white p-3 text-sm text-slate-700">
                    <p className="font-semibold">Forecast</p>
                    <p>{overview?.prediction?.trend}</p>
                    <p className="mt-1">Horizon: {overview?.prediction?.horizon_days || 2} days</p>
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="font-semibold text-slate-900">Top XAI factors</p>
                  <div className="mt-3 space-y-2 text-sm">
                    {(overview?.xai || []).length === 0 ? <p className="text-slate-500">Submit logs to generate explainability factors.</p> : overview.xai.slice(0, 6).map((item) => (
                      <div key={`${item.feature}-${item.impact}`} className="rounded-xl bg-white p-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-slate-800">{item.feature}</span>
                          <span className="text-rose-700">+{item.impact}</span>
                        </div>
                        <p className="text-slate-500">{item.reason}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Recovery timeline and wearable trends">
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={timeline}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="health_score" stroke="#059669" strokeWidth={2} />
                      <Line type="monotone" dataKey="risk_score" stroke="#e11d48" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={wearableChart}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="sleep" stroke="#2563eb" strokeWidth={2} />
                      <Line type="monotone" dataKey="stress" stroke="#f97316" strokeWidth={2} />
                      <Line type="monotone" dataKey="steps" stroke="#7c3aed" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {(overview?.timeline?.milestones || []).map((item) => <div key={item} className="rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-800">{item}</div>)}
              </div>
            </SectionCard>
          </div>

          <div className="space-y-4">
            <SectionCard title="Emergency SOS" subtitle="Escalates to caregiver, doctor, and admin.">
              <button onClick={triggerSos} className="w-full rounded-2xl bg-rose-600 py-3 font-semibold text-white">Trigger SOS</button>
              <div className="mt-3 rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">
                Emergency contact: {patient?.emergency_contact_name || "Not set"} {patient?.emergency_contact_phone ? `(${patient.emergency_contact_phone})` : ""}
              </div>
            </SectionCard>

            <SectionCard title="Wearable integration">
              <div className="grid gap-3 text-sm">
                <input className="rounded-2xl border border-slate-200 p-3" value={wearableForm.source} onChange={(e) => setWearableForm((p) => ({ ...p, source: e.target.value }))} />
                <input type="date" className="rounded-2xl border border-slate-200 p-3" value={wearableForm.metric_date} onChange={(e) => setWearableForm((p) => ({ ...p, metric_date: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Heart rate" value={wearableForm.heart_rate} onChange={(e) => setWearableForm((p) => ({ ...p, heart_rate: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Sleep hours" value={wearableForm.sleep_hours} onChange={(e) => setWearableForm((p) => ({ ...p, sleep_hours: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Steps" value={wearableForm.steps} onChange={(e) => setWearableForm((p) => ({ ...p, steps: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Stress 0-10" value={wearableForm.stress_level} onChange={(e) => setWearableForm((p) => ({ ...p, stress_level: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Oxygen saturation" value={wearableForm.oxygen_saturation} onChange={(e) => setWearableForm((p) => ({ ...p, oxygen_saturation: e.target.value }))} />
                <div className="grid gap-2 md:grid-cols-2">
                  <button onClick={() => syncWearable(false)} className="rounded-2xl bg-slate-900 py-3 text-white">Save sample</button>
                  <button onClick={() => syncWearable(true)} className="rounded-2xl bg-slate-200 py-3 text-slate-800">Demo sync</button>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Medication adherence">
              <p className="text-sm text-slate-600">7-day score: {adherence?.summary?.adherence_score ?? overview?.adherence?.adherence_score ?? 0}%</p>
              <div className="mt-3 space-y-3">
                {(dashboard?.medications || []).length === 0 ? <p className="text-sm text-slate-500">No active medicines.</p> : dashboard.medications.map((med) => (
                  <div key={med.id} className="rounded-2xl bg-slate-50 p-3 text-sm">
                    <p className="font-semibold text-slate-900">{med.medicine_name}</p>
                    <p className="text-slate-500">{med.dosage} - {med.timing}</p>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <button onClick={() => markMedication(med, true)} className="rounded-xl bg-emerald-600 px-3 py-2 text-white">Taken</button>
                      <button onClick={() => markMedication(med, false)} className="rounded-xl bg-rose-100 px-3 py-2 text-rose-700">Missed</button>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Voice and mood assistant">
              <textarea className="w-full rounded-2xl border border-slate-200 p-3 text-sm" rows="3" value={voiceText} onChange={(e) => setVoiceText(e.target.value)} />
              <button onClick={parseVoice} className="mt-2 w-full rounded-2xl bg-slate-900 py-3 text-white">Create voice log draft</button>
              {voiceDraft ? (
                <div className="mt-3 rounded-3xl border border-emerald-100 bg-gradient-to-br from-emerald-50 via-white to-sky-50 p-4 text-sm text-slate-700 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-emerald-600">Voice assistant</p>
                      <h3 className="mt-1 text-lg font-black text-slate-950">Daily log draft created</h3>
                    </div>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-emerald-700 shadow-sm">
                      {Math.round((voiceDraft.confidence || 0) * 100)}% confidence
                    </span>
                  </div>
                  <p className="mt-3 text-slate-600">
                    I found these symptoms in your voice note and prepared a simple check-in draft. Please review it before saving your daily log.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(voiceDraft.detected_symptoms?.length ? voiceDraft.detected_symptoms : ["No specific symptom detected"]).map((symptom) => (
                      <span key={symptom} className="rounded-full bg-white px-3 py-1 text-xs font-bold capitalize text-slate-700 shadow-sm">
                        {symptom}
                      </span>
                    ))}
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {[
                      ["Pain", `${voiceDraft.draft_log?.pain_score ?? "N/A"}/10`],
                      ["Mood", `${voiceDraft.draft_log?.mood_score ?? "N/A"}/5`],
                      ["Mobility", `${voiceDraft.draft_log?.mobility_score ?? "N/A"}/5`],
                      ["Fatigue", `${voiceDraft.draft_log?.fatigue_score ?? "N/A"}/10`]
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-2xl bg-white p-3 shadow-sm">
                        <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{label}</p>
                        <p className="mt-1 text-xl font-black text-slate-950">{value}</p>
                      </div>
                    ))}
                  </div>
                  {voiceDraft.draft_log?.symptom_notes ? (
                    <p className="mt-3 rounded-2xl bg-white p-3 text-slate-600 shadow-sm">
                      {voiceDraft.draft_log.symptom_notes}
                    </p>
                  ) : null}
                  <button onClick={() => navigate("/checkin")} className="mt-4 w-full rounded-2xl bg-white py-3 font-bold text-slate-900 shadow-sm transition hover:-translate-y-0.5 hover:bg-emerald-100">
                    Review in daily log
                  </button>
                </div>
              ) : null}
              <textarea className="mt-3 w-full rounded-2xl border border-slate-200 p-3 text-sm" rows="3" value={emotionText} onChange={(e) => setEmotionText(e.target.value)} />
              <button onClick={analyzeEmotion} className="mt-2 w-full rounded-2xl bg-slate-200 py-3 text-slate-800">Analyze mood</button>
              {emotion ? <div className="mt-3 rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">{emotion.dominant_emotion} - {emotion.support_message}</div> : null}
            </SectionCard>

            <SectionCard title="Reports and exports">
              <div className="grid gap-2">
                <a className="rounded-2xl bg-slate-900 px-4 py-3 text-center text-white" href={patient ? reportUrl("pdf") : "#"} target="_blank" rel="noreferrer">Download PDF report</a>
                <a className="rounded-2xl bg-slate-200 px-4 py-3 text-center text-slate-800" href={patient ? reportUrl("csv") : "#"} target="_blank" rel="noreferrer">Export Excel CSV</a>
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
