import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AlertBadge from "../components/AlertBadge";
import Navbar from "../components/Navbar";
import NotificationList from "../components/NotificationList";
import SectionCard from "../components/SectionCard";
import StatCard from "../components/StatCard";
import api from "../services/api";

export default function PatientDashboard() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [message, setMessage] = useState("");

  const loadData = async () => {
    try {
      const [dashboardRes, notificationRes] = await Promise.all([
        api.get(`/patients/by-user/${user.user_id}/dashboard`),
        api.get(`/notifications/${user.user_id}`),
      ]);
      if (dashboardRes.data.onboarding_required) {
        navigate("/onboarding");
        return;
      }
      setData(dashboardRes.data);
      setNotifications(notificationRes.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load dashboard");
    }
  };

  useEffect(() => {
    if (user?.user_id) loadData();
  }, [user?.user_id]);

  const chartData = useMemo(() => (data?.logs || []).map((log) => ({
    date: log.log_date,
    pain: log.pain_score,
    temp: log.temperature,
    risk: log.risk_score,
    sleep: log.sleep_hours,
  })), [data]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#dbeafe,_#f8fafc_40%,_#ecfccb_100%)] p-4">
      <div className="mx-auto max-w-7xl space-y-4">
        <Navbar title="Patient Dashboard" />
        {message ? <div className="rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">{message}</div> : null}

        <div className="grid gap-4 md:grid-cols-5">
          <StatCard label="Risk level" value={data?.latest_risk?.risk_level || "N/A"} hint="Updated after every log" />
          <StatCard label="Risk score" value={data?.latest_risk?.risk_score ?? 0} hint="Stored in database" />
          <StatCard label="Relapse forecast" value={`${data?.advanced?.prediction?.probability ?? 0}%`} hint={data?.advanced?.prediction?.trend || "Predictive monitoring"} />
          <StatCard label="Open alerts" value={data?.alerts?.length || 0} hint="High and critical alerts reach caregiver/admin" />
          <StatCard label="Today log status" value={data?.has_today_log ? "Done" : "Pending"} hint="Daily logging is mandatory" />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <SectionCard title="Flow status" subtitle="Registration -> login -> homepage -> dashboard -> onboarding -> daily log -> risk -> plan -> dashboard">
              <div className="grid gap-3 md:grid-cols-3">
                <Link to="/checkin" className="rounded-2xl bg-slate-900 px-4 py-3 text-center font-medium text-white">Submit daily log</Link>
                <Link to="/ai-health" className="rounded-2xl bg-emerald-600 px-4 py-3 text-center font-medium text-white">Open AI center</Link>
                <Link to="/onboarding" className="rounded-2xl bg-slate-200 px-4 py-3 text-center font-medium text-slate-800">Update onboarding</Link>
              </div>
            </SectionCard>

            <SectionCard title="Risk result and explanation" subtitle="Stored after each daily log">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="flex items-center justify-between"><p className="text-sm text-slate-500">Latest risk</p><AlertBadge level={data?.latest_risk?.risk_level} /></div>
                  <p className="mt-3 text-4xl font-bold text-slate-900">{data?.latest_risk?.risk_score ?? 0}</p>
                  <ul className="mt-4 space-y-1 text-sm text-slate-700">{(data?.latest_risk?.explanation || ["Submit a daily log to activate trend analysis."]).slice(0, 5).map((item, idx) => <li key={idx}>- {item}</li>)}</ul>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Recommendation logic</p>
                  <p className="mt-2 text-sm text-slate-700">If both symptom trends and camera signals are present, the dashboard shows both common and personalized recommendations. If not, it shows common recommendations and suggests adding richer inputs for personalization.</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="font-semibold text-slate-900">Common</p>
                      <ul className="mt-2 space-y-1 text-sm text-slate-700">{(data?.latest_risk?.recommendations_common || []).map((item, idx) => <li key={idx}>- {item}</li>)}</ul>
                    </div>
                    <div>
                      <p className="font-semibold text-slate-900">Personalized</p>
                      <ul className="mt-2 space-y-1 text-sm text-slate-700">{(data?.latest_risk?.recommendations_personalized || []).map((item, idx) => <li key={idx}>- {item}</li>)}</ul>
                    </div>
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Smart recommendations and milestones" subtitle="Generated from symptoms, medicine adherence, and wearable data.">
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="space-y-3">
                  {(data?.advanced?.recommendations || []).map((item) => (
                    <div key={`${item.category}-${item.text}`} className="rounded-2xl bg-slate-50 p-3 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold text-slate-900">{item.category}</p>
                        <span className="rounded-full bg-slate-200 px-2 py-1 text-xs text-slate-700">{item.priority}</span>
                      </div>
                      <p className="mt-1 text-slate-600">{item.text}</p>
                    </div>
                  ))}
                </div>
                <div className="space-y-3">
                  {(data?.advanced?.timeline?.milestones || []).map((item) => <div key={item} className="rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-800">{item}</div>)}
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Historical visualization" subtitle="Better representation of the patient recovery history">
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="pain" strokeWidth={2} name="Pain" />
                      <Line type="monotone" dataKey="temp" strokeWidth={2} name="Temperature" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="risk" strokeWidth={2} name="Risk score" />
                      <Area type="monotone" dataKey="sleep" strokeWidth={2} name="Sleep hours" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </SectionCard>
          </div>

          <div className="space-y-4">
            <SectionCard title="Recovery plan" subtitle="Generated after onboarding">
              <p className="text-sm text-slate-700">{data?.plan?.summary || "No plan generated yet."}</p>
              <div className="mt-3 grid gap-3">
                {(data?.plan?.daily_tasks || []).map((task, idx) => <div key={idx} className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">- {task}</div>)}
              </div>
            </SectionCard>

            <SectionCard title="Medication tracking">
              <div className="space-y-3 text-sm text-slate-700">
                {(data?.medications || []).length === 0 ? <p>No medication plan added yet.</p> : data.medications.map((med) => (
                  <div key={med.id} className="rounded-2xl bg-slate-50 p-3">
                    <p className="font-semibold">{med.medicine_name}</p>
                    <p>{med.dosage} - {med.timing}</p>
                    <p className="text-slate-500">{med.instructions}</p>
                  </div>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Notifications" subtitle="Daily reminder and risk updates appear here">
              <NotificationList items={notifications} />
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
