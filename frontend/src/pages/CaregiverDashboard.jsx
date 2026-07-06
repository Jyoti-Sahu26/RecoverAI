import { useEffect, useState } from "react";
import AlertBadge from "../components/AlertBadge";
import Navbar from "../components/Navbar";
import NotificationList from "../components/NotificationList";
import SectionCard from "../components/SectionCard";
import StatCard from "../components/StatCard";
import api from "../services/api";

export default function CaregiverDashboard() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      const res = await api.get(`/caregivers/${user.user_id}/dashboard`);
      setData(res.data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load caregiver dashboard");
    }
  };

  useEffect(() => { if (user?.user_id) load(); }, [user?.user_id]);

  const acknowledge = async (alertId) => {
    try {
      await api.post(`/caregivers/${user.user_id}/alerts/acknowledge`, { alert_id: alertId });
      load();
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to acknowledge alert");
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fee2e2,_#f8fafc_45%,_#dbeafe_100%)] p-4">
      <div className="mx-auto max-w-7xl space-y-4">
        <Navbar title="Caregiver Dashboard" />
        {message ? <div className="rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">{message}</div> : null}
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard label="Linked patients" value={data?.counts?.linked_patients || 0} />
          <StatCard label="Active alerts" value={data?.counts?.active_alerts || 0} />
          <StatCard label="Recent logs" value={data?.counts?.recent_logs || 0} />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <SectionCard title="Priority view" subtitle="Patients sorted by current risk score">
              <div className="space-y-3">
                {(data?.priority_patients || []).length === 0 ? <p className="text-sm text-slate-500">No linked patients yet.</p> : data.priority_patients.map((item) => (
                  <div key={item.patient_id} className="rounded-2xl bg-slate-50 p-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-lg font-semibold text-slate-900">{item.patient_name}</p>
                        <p className="text-sm text-slate-500">{item.diagnosis} - {item.plan_phase || "Plan pending"}</p>
                      </div>
                      <div className="flex items-center gap-2"><AlertBadge level={item.risk?.risk_level} /><span className="text-sm text-slate-600">Score {item.risk?.risk_score ?? 0}</span></div>
                    </div>
                    <div className="mt-3 text-sm text-slate-700">{(item.risk?.explanation || ["No recent logs yet."]).slice(0, 3).map((reason, idx) => <p key={idx}>- {reason}</p>)}</div>
                  </div>
                ))}
              </div>
            </SectionCard>
            <SectionCard title="Missed-alert notifications" subtitle="Caregiver reminder if an alert remains unacknowledged">
              <NotificationList items={data?.notifications || []} />
            </SectionCard>
          </div>
          <div>
            <SectionCard title="Latest alerts" subtitle="High and critical alerts trigger emergency notification">
              <div className="space-y-3 text-sm text-slate-700">
                {(data?.alerts || []).length === 0 ? <p>No alerts yet.</p> : data.alerts.map((alert) => (
                  <div key={alert.id} className="rounded-2xl bg-slate-50 p-3">
                    <div className="flex items-center justify-between"><AlertBadge level={alert.level} /><span className="text-xs text-slate-500">Patient #{alert.patient_id}</span></div>
                    <p className="mt-2 font-medium">{alert.reason}</p>
                    <p className="mt-1 text-slate-500">{alert.explanation}</p>
                    <button onClick={() => acknowledge(alert.id)} className="mt-3 rounded-xl bg-slate-900 px-3 py-2 text-xs text-white">Acknowledge</button>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}
