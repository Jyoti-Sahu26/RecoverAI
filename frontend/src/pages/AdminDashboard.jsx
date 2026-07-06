import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AlertBadge from "../components/AlertBadge";
import Navbar from "../components/Navbar";
import NotificationList from "../components/NotificationList";
import SectionCard from "../components/SectionCard";
import StatCard from "../components/StatCard";
import api from "../services/api";

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [riskMap, setRiskMap] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryRes, alertsRes, notificationsRes, analyticsRes, riskMapRes] = await Promise.all([
          api.get("/admin/summary"),
          api.get("/admin/alerts"),
          api.get("/admin/notifications"),
          api.get("/admin/analytics"),
          api.get("/advanced/admin/risk-map"),
        ]);
        setSummary(summaryRes.data);
        setAlerts(alertsRes.data);
        setNotifications(notificationsRes.data);
        setAnalytics(analyticsRes.data);
        setRiskMap(riskMapRes.data);
      } catch (error) {
        setMessage(error?.response?.data?.detail || "Failed to load admin dashboard");
      }
    };
    load();
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fce7f3,_#f8fafc_45%,_#dbeafe_100%)] p-4">
      <div className="mx-auto max-w-7xl space-y-4">
        <Navbar title="Admin Dashboard" />
        {message ? <div className="rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">{message}</div> : null}
        <div className="grid gap-4 md:grid-cols-7">
          <StatCard label="Users" value={summary?.total_users || 0} />
          <StatCard label="Patients" value={summary?.total_patients || 0} />
          <StatCard label="Caregivers" value={summary?.caregivers || 0} />
          <StatCard label="Doctors" value={summary?.doctors || 0} />
          <StatCard label="Alerts" value={summary?.total_alerts || 0} />
          <StatCard label="Critical" value={summary?.critical_alerts || 0} />
          <StatCard label="Unread notifications" value={summary?.unread_notifications || 0} />
        </div>
        <SectionCard title="Healthcare analytics" subtitle="Startup-style KPIs for active users, risk distribution, recovery success, and alert frequency.">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={Object.entries(analytics?.kpis?.risk_distribution || {}).map(([level, count]) => ({ level, count }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="level" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0f766e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics?.recent_recovery_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="risk_score" stroke="#e11d48" strokeWidth={2} />
                  <Line type="monotone" dataKey="sleep" stroke="#2563eb" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <StatCard label="Active users" value={analytics?.kpis?.active_users || 0} />
            <StatCard label="Success rate" value={`${analytics?.kpis?.recovery_success_rate || 0}%`} />
            <StatCard label="Wearable samples" value={analytics?.kpis?.wearable_samples || 0} />
            <StatCard label="Emergency events" value={summary?.emergency_events || 0} />
          </div>
        </SectionCard>
        <SectionCard title="AI health risk map" subtitle="Common symptom clusters, alert distribution, and recovery trend mapping for admin insight.">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="h-64 lg:col-span-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={riskMap?.risk_trends || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="avg_risk" stroke="#dc2626" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2">
              {(riskMap?.common_symptoms || []).length === 0 ? <p className="text-sm text-slate-500">No symptom cluster data yet.</p> : riskMap.common_symptoms.map((item) => (
                <div key={item.symptom} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm">
                  <span className="font-semibold capitalize text-slate-800">{item.symptom}</span>
                  <span className="rounded-full bg-rose-100 px-2 py-1 text-rose-700">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <SectionCard title="System alert stream" subtitle="Admin sees all escalations">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {alerts.length === 0 ? <p className="text-sm text-slate-500">No alerts yet.</p> : alerts.map((alert) => (
                  <div key={alert.id} className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                    <div className="flex items-center justify-between"><AlertBadge level={alert.level} /><span>Patient #{alert.patient_id}</span></div>
                    <p className="mt-3 font-medium text-slate-900">{alert.reason}</p>
                    <p className="mt-2 text-slate-500">{alert.explanation}</p>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>
          <div>
            <SectionCard title="Notification stream">
              <NotificationList items={notifications} />
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
