import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Navbar from "../components/Navbar";
import SectionCard from "../components/SectionCard";
import StatCard from "../components/StatCard";
import api from "../services/api";

const today = () => new Date().toISOString().split("T")[0];

function MiniHeatmap({ cells }) {
  const colors = { good: "bg-emerald-400", moderate: "bg-amber-400", severe: "bg-rose-500" };
  return (
    <div className="grid grid-cols-[repeat(15,minmax(0,1fr))] gap-1">
      {(cells || []).slice(-60).map((cell) => (
        <div
          key={cell.date}
          title={`${cell.date}: ${cell.state}`}
          className={`h-4 rounded ${colors[cell.state] || "bg-slate-200"} shadow-sm`}
        />
      ))}
    </div>
  );
}

export default function AdvancedRecoveryHub() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [hub, setHub] = useState(null);
  const [message, setMessage] = useState("");
  const [habit, setHabit] = useState({
    habit_date: today(),
    water_glasses: 7,
    meditation_minutes: 10,
    exercise_minutes: 15,
    breathing_sessions: 2,
    screen_time_hours: 4,
    sleep_quality: 7,
  });
  const [journalText, setJournalText] = useState("I slept better today but still feel a little anxious about pain.");
  const [meal, setMeal] = useState({ plan_date: today(), allergies: "", nutrition_goal: "fatigue recovery and hydration" });
  const [goal, setGoal] = useState({ goal_type: "sleep", target_value: 8, unit: "hours", current_value: 6 });
  const [collab, setCollab] = useState({ item_type: "task", title: "Evening walk", body: "Complete a supervised 10 minute walk.", status: "open" });
  const [prescriptionText, setPrescriptionText] = useState("Paracetamol 500mg after food daily\nVitamin C 500mg after food daily");
  const [recordText, setRecordText] = useState("Hemoglobin stable. Mild inflammation markers. Continue hydration and medication adherence.");
  const [thread, setThread] = useState({ title: "How do you manage fatigue?", body: "Looking for recovery-safe tips.", anonymous: true });
  const [simulation, setSimulation] = useState({ sleep_gain_hours: 1, medication_adherence_gain: 15, exercise_gain_minutes: 15, stress_reduction: 2 });
  const [simulationResult, setSimulationResult] = useState(null);
  const [adaptiveHint, setAdaptiveHint] = useState("headache and nausea");
  const [adaptive, setAdaptive] = useState(null);
  const [cameraResult, setCameraResult] = useState(null);
  const [liveStatus, setLiveStatus] = useState("Connecting after patient profile loads...");

  const load = async () => {
    try {
      const profileRes = await api.get(`/patients/profile/by-user/${user.user_id}`);
      if (!profileRes.data.patient) {
        navigate("/onboarding");
        return;
      }
      const activePatient = profileRes.data.patient;
      setPatient(activePatient);
      const hubRes = await api.get(`/advanced/patients/${activePatient.id}/hub`);
      setHub(hubRes.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load advanced recovery hub");
    }
  };

  useEffect(() => {
    if (user?.user_id) load();
  }, [user?.user_id]);

  useEffect(() => {
    if (!patient?.id) return undefined;
    const socket = new WebSocket(`ws://127.0.0.1:8000/api/advanced/patients/${patient.id}/live`);
    socket.onopen = () => setLiveStatus("Live monitoring connected");
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLiveStatus(`Live score ${data.recovery_score?.score}/100 - ${data.smart_notifications?.[0] || "stable"}`);
    };
    socket.onerror = () => setLiveStatus("Live monitoring ready when backend is restarted");
    socket.onclose = () => setLiveStatus("Live monitoring paused");
    return () => socket.close();
  }, [patient?.id]);

  const postAndReload = async (url, payload, success) => {
    try {
      await api.post(url, payload);
      await load();
      setMessage(success);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Action failed");
    }
  };

  const chartData = useMemo(() => (hub?.heatmap || []).map((cell) => ({
    date: cell.date,
    risk: cell.risk_score,
    pain: cell.pain,
  })), [hub]);

  const addHabit = () => postAndReload(`/advanced/patients/${patient.id}/habits`, {
    ...habit,
    water_glasses: Number(habit.water_glasses),
    meditation_minutes: Number(habit.meditation_minutes),
    exercise_minutes: Number(habit.exercise_minutes),
    breathing_sessions: Number(habit.breathing_sessions),
    screen_time_hours: Number(habit.screen_time_hours),
    sleep_quality: Number(habit.sleep_quality),
  }, "Habit saved and recovery correlations refreshed.");

  const addJournal = () => postAndReload(`/advanced/patients/${patient.id}/journal`, {
    user_id: user.user_id,
    journal_date: today(),
    text: journalText,
  }, "Journal saved with AI mood insight.");

  const generateMeal = () => postAndReload(`/advanced/patients/${patient.id}/meal-plan`, meal, "AI meal plan generated.");

  const addGoal = () => postAndReload(`/advanced/patients/${patient.id}/goals`, {
    ...goal,
    target_value: Number(goal.target_value),
    current_value: Number(goal.current_value),
  }, "Smart recovery goal saved.");

  const addCollab = () => postAndReload(`/advanced/patients/${patient.id}/collaboration`, {
    ...collab,
    created_by_user_id: user.user_id,
  }, "Collaboration item shared.");

  const scanPrescription = () => postAndReload(`/advanced/patients/${patient.id}/prescription-scan`, {
    raw_text: prescriptionText,
    auto_add_medications: true,
  }, "Prescription OCR extracted medicines and added reminders.");

  const addRecord = () => postAndReload(`/advanced/patients/${patient.id}/records`, {
    uploaded_by_user_id: user.user_id,
    record_type: "lab_report",
    file_name: "lab-report-demo.txt",
    content_text: recordText,
  }, "Medical record stored in secure vault.");

  const createThread = () => postAndReload("/advanced/community/threads", {
    ...thread,
    patient_id: patient.id,
    user_id: user.user_id,
  }, "Anonymous community thread created with AI moderation.");

  const runSimulation = async () => {
    try {
      const res = await api.post(`/advanced/patients/${patient.id}/simulate`, {
        sleep_gain_hours: Number(simulation.sleep_gain_hours),
        medication_adherence_gain: Number(simulation.medication_adherence_gain),
        exercise_gain_minutes: Number(simulation.exercise_gain_minutes),
        stress_reduction: Number(simulation.stress_reduction),
      });
      setSimulationResult(res.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Simulation failed");
    }
  };

  const runAdaptive = async () => {
    try {
      const res = await api.post(`/advanced/patients/${patient.id}/adaptive-checkin`, { symptom_hint: adaptiveHint });
      setAdaptive(res.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Adaptive check-in failed");
    }
  };

  const runCamera = async () => {
    try {
      const res = await api.post(`/advanced/patients/${patient.id}/camera-severity`, {
        image_type: "skin",
        redness_index: 0.35,
        swelling_index: 0.3,
        discoloration_index: 0.2,
        pain_expression_index: 0.25,
      });
      setCameraResult(res.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Camera severity failed");
    }
  };

  return (
    <div className="min-h-screen p-4">
      <div className="mx-auto max-w-7xl space-y-5">
        <Navbar title="Advanced Recovery Hub" />
        {message ? <div className="rounded-2xl bg-white/90 p-3 text-sm font-medium text-slate-700 shadow-lg">{message}</div> : null}

        <section className="relative overflow-hidden rounded-[2rem] bg-slate-950 p-6 text-white shadow-[0_30px_90px_rgba(15,23,42,0.28)]">
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 via-sky-400 to-fuchsia-400" />
          <div className="relative grid gap-5 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.35em] text-emerald-200">Digital twin workspace</p>
              <h2 className="mt-4 text-4xl font-black tracking-tight md:text-5xl">A startup-grade AI layer for predictive recovery.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">{hub?.digital_twin?.summary || "Building patient digital twin..."}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-300">Relapse</p>
                <p className="mt-2 text-3xl font-black">{hub?.digital_twin?.relapse_probability ?? 0}%</p>
              </div>
              <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-300">Velocity</p>
                <p className="mt-2 text-3xl font-black">{hub?.digital_twin?.recovery_velocity ?? 0}</p>
              </div>
              <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-300">Projected</p>
                <p className="mt-2 text-3xl font-black">{hub?.digital_twin?.projected_recovery_days ?? 0}d</p>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-4 md:grid-cols-4">
          <StatCard label="AI Recovery Score" value={`${hub?.recovery_score?.score ?? 0}/100`} hint={hub?.recovery_score?.status || "Live scoring"} />
          <StatCard label="XP Points" value={hub?.rewards?.xp ?? 0} hint={hub?.rewards?.badges?.join(", ")} />
          <StatCard label="Avg Sleep" value={`${hub?.sleep_analysis?.avg_sleep ?? 0}h`} hint={hub?.sleep_analysis?.quality} />
          <StatCard label="Smart Alerts" value={hub?.smart_notifications?.length ?? 0} hint={hub?.smart_notifications?.[0]} />
        </div>

        <SectionCard title="Real-time and multi-language readiness" subtitle="WebSocket-powered live monitoring with India-focused language support.">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-800">
              <p className="font-bold">Live dashboard</p>
              <p className="mt-1">{liveStatus}</p>
            </div>
            {["English", "Hindi", "Marathi"].map((language) => (
              <div key={language} className="rounded-2xl bg-sky-50 p-4 text-sm text-sky-800">
                <p className="font-bold">{language}</p>
                <p className="mt-1">Recovery education, reminders, and coaching-ready.</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="grid gap-5 xl:grid-cols-3">
          <div className="space-y-5 xl:col-span-2">
            <SectionCard title="Recovery heatmap and timeline" subtitle="GitHub-style health intensity plus symptom trend lines.">
              <MiniHeatmap cells={hub?.heatmap || []} />
              <div className="mt-5 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="risk" stroke="#e11d48" strokeWidth={2} />
                    <Line type="monotone" dataKey="pain" stroke="#0ea5e9" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard title="AI recovery coach and report summarizer">
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl bg-emerald-50 p-4">
                  <p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-700">Coach</p>
                  <p className="mt-3 text-lg font-bold text-slate-950">{hub?.coach?.message}</p>
                  <p className="mt-2 text-sm text-slate-600">{hub?.coach?.action}</p>
                </div>
                <div className="rounded-2xl bg-sky-50 p-4">
                  <p className="text-sm font-bold uppercase tracking-[0.2em] text-sky-700">Doctor summary</p>
                  <p className="mt-3 text-sm leading-6 text-slate-700">{hub?.report_summary}</p>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Smart habit tracker and health journal" subtitle={hub?.habit_insights?.summary}>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="grid gap-3">
                  <input type="date" className="rounded-2xl border border-slate-200 p-3" value={habit.habit_date} onChange={(e) => setHabit((p) => ({ ...p, habit_date: e.target.value }))} />
                  {["water_glasses", "meditation_minutes", "exercise_minutes", "breathing_sessions", "screen_time_hours", "sleep_quality"].map((key) => (
                    <input key={key} type="number" className="rounded-2xl border border-slate-200 p-3" placeholder={key.replace(/_/g, " ")} value={habit[key]} onChange={(e) => setHabit((p) => ({ ...p, [key]: e.target.value }))} />
                  ))}
                  <button onClick={addHabit} className="rounded-2xl bg-emerald-600 py-3 font-semibold text-white">Save habit entry</button>
                </div>
                <div>
                  <textarea className="h-48 w-full rounded-2xl border border-slate-200 p-3" value={journalText} onChange={(e) => setJournalText(e.target.value)} />
                  <button onClick={addJournal} className="mt-3 w-full rounded-2xl bg-slate-900 py-3 font-semibold text-white">Analyze journal</button>
                  <div className="mt-3 space-y-2 text-sm">
                    {(hub?.journals || []).slice(0, 3).map((item) => (
                      <div key={item.id} className="rounded-2xl bg-slate-50 p-3">
                        <p className="font-semibold text-slate-900">{item.emotion} - stress {item.stress_score}</p>
                        <p className="text-slate-500">{item.ai_insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Family collaboration and community support">
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="grid gap-3">
                  <input className="rounded-2xl border border-slate-200 p-3" value={collab.title} onChange={(e) => setCollab((p) => ({ ...p, title: e.target.value }))} />
                  <textarea className="rounded-2xl border border-slate-200 p-3" rows="3" value={collab.body} onChange={(e) => setCollab((p) => ({ ...p, body: e.target.value }))} />
                  <button onClick={addCollab} className="rounded-2xl bg-sky-600 py-3 font-semibold text-white">Share with care team</button>
                  {(hub?.collaboration || []).slice(0, 4).map((item) => <div key={item.id} className="rounded-xl bg-sky-50 p-3 text-sm">{item.title} - {item.status}</div>)}
                </div>
                <div className="grid gap-3">
                  <input className="rounded-2xl border border-slate-200 p-3" value={thread.title} onChange={(e) => setThread((p) => ({ ...p, title: e.target.value }))} />
                  <textarea className="rounded-2xl border border-slate-200 p-3" rows="3" value={thread.body} onChange={(e) => setThread((p) => ({ ...p, body: e.target.value }))} />
                  <button onClick={createThread} className="rounded-2xl bg-violet-600 py-3 font-semibold text-white">Create anonymous support thread</button>
                </div>
              </div>
            </SectionCard>
          </div>

          <div className="space-y-5">
            <SectionCard title="AI meal planner">
              <input className="w-full rounded-2xl border border-slate-200 p-3" placeholder="Allergies" value={meal.allergies} onChange={(e) => setMeal((p) => ({ ...p, allergies: e.target.value }))} />
              <input className="mt-3 w-full rounded-2xl border border-slate-200 p-3" value={meal.nutrition_goal} onChange={(e) => setMeal((p) => ({ ...p, nutrition_goal: e.target.value }))} />
              <button onClick={generateMeal} className="mt-3 w-full rounded-2xl bg-emerald-600 py-3 font-semibold text-white">Generate meal plan</button>
              {(hub?.meal_plans?.[0]?.meals || []).slice(0, 4).map((item) => <div key={item.time} className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm"><b>{item.time}</b>: {item.meal}</div>)}
            </SectionCard>

            <SectionCard title="Smart recovery goals">
              <div className="grid gap-3">
                <input className="rounded-2xl border border-slate-200 p-3" value={goal.goal_type} onChange={(e) => setGoal((p) => ({ ...p, goal_type: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" value={goal.target_value} onChange={(e) => setGoal((p) => ({ ...p, target_value: e.target.value }))} />
                <input className="rounded-2xl border border-slate-200 p-3" value={goal.unit} onChange={(e) => setGoal((p) => ({ ...p, unit: e.target.value }))} />
                <input type="number" className="rounded-2xl border border-slate-200 p-3" value={goal.current_value} onChange={(e) => setGoal((p) => ({ ...p, current_value: e.target.value }))} />
                <button onClick={addGoal} className="rounded-2xl bg-slate-900 py-3 font-semibold text-white">Save goal</button>
                {(hub?.goals || []).slice(0, 3).map((item) => <div key={item.id} className="rounded-xl bg-slate-50 p-3 text-sm">{item.goal_type}: {item.current_value}/{item.target_value} {item.unit}</div>)}
              </div>
            </SectionCard>

            <SectionCard title="OCR prescription scanner and record vault">
              <textarea className="w-full rounded-2xl border border-slate-200 p-3" rows="4" value={prescriptionText} onChange={(e) => setPrescriptionText(e.target.value)} />
              <button onClick={scanPrescription} className="mt-3 w-full rounded-2xl bg-amber-500 py-3 font-semibold text-white">Scan prescription</button>
              <textarea className="mt-3 w-full rounded-2xl border border-slate-200 p-3" rows="3" value={recordText} onChange={(e) => setRecordText(e.target.value)} />
              <button onClick={addRecord} className="mt-3 w-full rounded-2xl bg-slate-900 py-3 font-semibold text-white">Store medical record</button>
            </SectionCard>

            <SectionCard title="Adaptive check-in and camera AI">
              <input className="w-full rounded-2xl border border-slate-200 p-3" value={adaptiveHint} onChange={(e) => setAdaptiveHint(e.target.value)} />
              <button onClick={runAdaptive} className="mt-3 w-full rounded-2xl bg-cyan-600 py-3 font-semibold text-white">Generate questions</button>
              {adaptive ? <ul className="mt-3 space-y-2 text-sm text-slate-700">{adaptive.questions.map((q) => <li key={q} className="rounded-xl bg-cyan-50 p-2">{q}</li>)}</ul> : null}
              <button onClick={runCamera} className="mt-3 w-full rounded-2xl bg-rose-600 py-3 font-semibold text-white">Analyze camera severity demo</button>
              {cameraResult ? <div className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{cameraResult.ai_observation}</div> : null}
            </SectionCard>

            <SectionCard title="AI recovery simulation">
              {[
                ["sleep_gain_hours", "Sleep gain hours"],
                ["medication_adherence_gain", "Adherence gain %"],
                ["exercise_gain_minutes", "Exercise gain minutes"],
                ["stress_reduction", "Stress reduction"],
              ].map(([key, label]) => (
                <input key={key} type="number" className="mb-3 w-full rounded-2xl border border-slate-200 p-3" placeholder={label} value={simulation[key]} onChange={(e) => setSimulation((p) => ({ ...p, [key]: e.target.value }))} />
              ))}
              <button onClick={runSimulation} className="w-full rounded-2xl bg-fuchsia-600 py-3 font-semibold text-white">Run what-if simulation</button>
              {simulationResult ? <div className="mt-3 rounded-xl bg-fuchsia-50 p-3 text-sm text-fuchsia-800">{simulationResult.summary}</div> : null}
            </SectionCard>

            <SectionCard title="Knowledge and smart notifications">
              <div className="space-y-3 text-sm">
                {(hub?.knowledge || []).slice(0, 4).map((item) => <div key={item.title} className="rounded-xl bg-slate-50 p-3"><b>{item.title}</b><p className="text-slate-500">{item.reason}</p></div>)}
              </div>
              <div className="mt-4 space-y-2 text-sm">
                {(hub?.smart_notifications || []).map((item) => <div key={item} className="rounded-xl bg-amber-50 p-2 text-amber-800">{item}</div>)}
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
