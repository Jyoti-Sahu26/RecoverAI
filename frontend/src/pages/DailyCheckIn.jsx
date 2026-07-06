import { useEffect, useState } from "react";
import AlertBadge from "../components/AlertBadge";
import Navbar from "../components/Navbar";
import SectionCard from "../components/SectionCard";
import api from "../services/api";

export default function DailyCheckIn() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const [patient, setPatient] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({
    log_date: new Date().toISOString().split("T")[0],
    pain_score: 5,
    temperature: 98.6,
    mood_score: 3,
    mobility_score: 3,
    sleep_hours: 7,
    meds_taken: true,
    meds_missed_count: 0,
    symptom_notes: "",
    engagement_minutes: 10,
    fatigue_score: 3,
    swelling_score: 2,
    wound_score: 2,
    voice_note: "",
    redness_index: 0.2,
    swelling_index: 0.2,
    fatigue_index: 0.2,
    pain_face_index: 0.2,
    skin_tone_index: 0.5,
  });

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/patients/profile/by-user/${user.user_id}`);
        if (res.data.patient) setPatient(res.data.patient);
      } catch (error) {
        setMessage(error?.response?.data?.detail || "Failed to load patient profile");
      }
    };
    load();
  }, [user?.user_id]);

  const submit = async () => {
    if (!patient) return;
    try {
      setLoading(true);
      setMessage("");
      await api.post(`/patients/${patient.id}/camera-scan`, {
        redness_index: Number(form.redness_index),
        swelling_index: Number(form.swelling_index),
        fatigue_index: Number(form.fatigue_index),
        pain_face_index: Number(form.pain_face_index),
        skin_tone_index: Number(form.skin_tone_index),
      });
      const res = await api.post(`/patients/${patient.id}/daily-log`, {
        log_date: form.log_date,
        pain_score: Number(form.pain_score),
        temperature: Number(form.temperature),
        mood_score: Number(form.mood_score),
        mobility_score: Number(form.mobility_score),
        sleep_hours: Number(form.sleep_hours),
        meds_taken: form.meds_taken,
        meds_missed_count: Number(form.meds_missed_count),
        symptom_notes: form.symptom_notes,
        engagement_minutes: Number(form.engagement_minutes),
        fatigue_score: Number(form.fatigue_score),
        swelling_score: Number(form.swelling_score),
        wound_score: Number(form.wound_score),
        voice_note: form.voice_note,
      });
      setResult(res.data);
      setMessage("Daily log submitted. Risk score stored successfully.");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to submit daily log");
    } finally {
      setLoading(false);
    }
  };

  const slider = (label, key, max = 10) => (
    <div>
      <label className="mb-2 block text-sm font-medium text-slate-700">{label}: {form[key]}</label>
      <input type="range" min="0" max={max} step="1" className="w-full" value={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))} />
    </div>
  );

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fef3c7,_#f8fafc_45%,_#dbeafe_100%)] p-4">
      <div className="mx-auto max-w-6xl space-y-4">
        <Navbar title="Daily symptom log" />
        {message ? <div className="rounded-2xl bg-slate-100 p-3 text-sm text-slate-700">{message}</div> : null}

        <div className="grid gap-4 xl:grid-cols-2">
          <SectionCard title="Mandatory daily log" subtitle="One submission per day is required.">
            <div className="grid gap-4">
              <input type="date" className="rounded-2xl border border-slate-200 p-3" value={form.log_date} onChange={(e) => setForm((prev) => ({ ...prev, log_date: e.target.value }))} />
              {slider("Pain score", "pain_score")}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Temperature</label>
                <input type="number" step="0.1" className="w-full rounded-2xl border border-slate-200 p-3" value={form.temperature} onChange={(e) => setForm((prev) => ({ ...prev, temperature: e.target.value }))} />
              </div>
              {slider("Mood score", "mood_score", 5)}
              {slider("Mobility score", "mobility_score", 5)}
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Sleep hours</label>
                  <input type="number" step="0.5" className="w-full rounded-2xl border border-slate-200 p-3" value={form.sleep_hours} onChange={(e) => setForm((prev) => ({ ...prev, sleep_hours: e.target.value }))} />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Engagement minutes</label>
                  <input type="number" className="w-full rounded-2xl border border-slate-200 p-3" value={form.engagement_minutes} onChange={(e) => setForm((prev) => ({ ...prev, engagement_minutes: e.target.value }))} />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="rounded-2xl border border-slate-200 p-3 text-sm">Medicine taken today?
                  <select className="mt-2 w-full rounded-xl border border-slate-200 p-2" value={String(form.meds_taken)} onChange={(e) => setForm((prev) => ({ ...prev, meds_taken: e.target.value === "true" }))}>
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                </label>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Missed doses</label>
                  <input type="number" className="w-full rounded-2xl border border-slate-200 p-3" value={form.meds_missed_count} onChange={(e) => setForm((prev) => ({ ...prev, meds_missed_count: e.target.value }))} />
                </div>
              </div>
              {slider("Fatigue score", "fatigue_score")}
              {slider("Swelling score", "swelling_score")}
              {slider("Wound concern score", "wound_score")}
              <textarea className="rounded-2xl border border-slate-200 p-3" rows="4" placeholder="Symptom notes" value={form.symptom_notes} onChange={(e) => setForm((prev) => ({ ...prev, symptom_notes: e.target.value }))} />
              <textarea className="rounded-2xl border border-slate-200 p-3" rows="3" placeholder="Voice note text / chatbot note" value={form.voice_note} onChange={(e) => setForm((prev) => ({ ...prev, voice_note: e.target.value }))} />
            </div>
          </SectionCard>

          <SectionCard title="Prototype smart camera inputs" subtitle="Use these structured indicators for better recommendations.">
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Skin color / oxygen / anemia hint</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full" value={form.skin_tone_index} onChange={(e) => setForm((prev) => ({ ...prev, skin_tone_index: e.target.value }))} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Redness</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full" value={form.redness_index} onChange={(e) => setForm((prev) => ({ ...prev, redness_index: e.target.value }))} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Swelling visual signal</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full" value={form.swelling_index} onChange={(e) => setForm((prev) => ({ ...prev, swelling_index: e.target.value }))} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Face fatigue signal</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full" value={form.fatigue_index} onChange={(e) => setForm((prev) => ({ ...prev, fatigue_index: e.target.value }))} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Face pain signal</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full" value={form.pain_face_index} onChange={(e) => setForm((prev) => ({ ...prev, pain_face_index: e.target.value }))} />
              </div>
              <button onClick={submit} disabled={loading} className="w-full rounded-2xl bg-slate-900 py-3 text-white disabled:opacity-50">{loading ? "Submitting..." : "Submit daily log and calculate risk"}</button>
            </div>
          </SectionCard>
        </div>

        {result?.risk ? (
          <SectionCard title="Risk score result and explanation" subtitle="Stored in database after this submission.">
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-3xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Risk score</p>
                <p className="mt-2 text-4xl font-bold text-slate-900">{result.risk.risk_score}</p>
                <div className="mt-3"><AlertBadge level={result.risk.risk_level} /></div>
              </div>
              <div className="rounded-3xl bg-slate-50 p-4 lg:col-span-2">
                <p className="text-sm text-slate-500">Explanation</p>
                <ul className="mt-3 space-y-2 text-sm text-slate-700">
                  {result.risk.explanation.map((item, idx) => <li key={idx}>- {item}</li>)}
                </ul>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="font-semibold text-slate-900">Common recommendations</p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-700">{result.risk.recommendations_common.map((item, idx) => <li key={idx}>- {item}</li>)}</ul>
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">Personalized recommendations</p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-700">{result.risk.recommendations_personalized.map((item, idx) => <li key={idx}>- {item}</li>)}</ul>
                  </div>
                </div>
              </div>
            </div>
          </SectionCard>
        ) : null}
      </div>
    </div>
  );
}
