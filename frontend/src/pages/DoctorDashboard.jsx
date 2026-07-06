import { useEffect, useState } from "react";
import AlertBadge from "../components/AlertBadge";
import Navbar from "../components/Navbar";
import SectionCard from "../components/SectionCard";
import StatCard from "../components/StatCard";
import api from "../services/api";

export default function DoctorDashboard() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const [data, setData] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState("");
  const [note, setNote] = useState({ note_type: "consultation", summary: "", prescription: "", follow_up_date: "" });
  const [appointment, setAppointment] = useState({ scheduled_at: "", reason: "", notes: "" });
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      const res = await api.get(`/doctors/${user.user_id}/dashboard`);
      setData(res.data);
      if (!selectedPatient && res.data.patients?.[0]?.patient?.id) {
        setSelectedPatient(String(res.data.patients[0].patient.id));
      }
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load doctor dashboard");
    }
  };

  useEffect(() => {
    if (user?.user_id) load();
  }, [user?.user_id]);

  const saveNote = async () => {
    if (!selectedPatient || !note.summary.trim()) return;
    try {
      await api.post(`/doctors/${user.user_id}/notes`, {
        patient_id: Number(selectedPatient),
        note_type: note.note_type,
        summary: note.summary,
        prescription: note.prescription,
        follow_up_date: note.follow_up_date || null,
      });
      setNote({ note_type: "consultation", summary: "", prescription: "", follow_up_date: "" });
      setMessage("Doctor note saved and patient notified.");
      load();
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to save note");
    }
  };

  const scheduleAppointment = async () => {
    if (!selectedPatient || !appointment.scheduled_at) return;
    try {
      await api.post(`/doctors/${user.user_id}/appointments`, {
        patient_id: Number(selectedPatient),
        scheduled_at: new Date(appointment.scheduled_at).toISOString(),
        reason: appointment.reason,
        notes: appointment.notes,
      });
      setAppointment({ scheduled_at: "", reason: "", notes: "" });
      setMessage("Appointment scheduled and notification sent.");
      load();
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to schedule appointment");
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#ede9fe,_#f8fafc_42%,_#dcfce7_100%)] p-4">
      <div className="mx-auto max-w-7xl space-y-4">
        <Navbar title="Doctor Portal" />
        {message ? <div className="rounded-2xl bg-slate-100 p-3 text-sm text-slate-700">{message}</div> : null}

        <div className="grid gap-4 md:grid-cols-4">
          <StatCard label="Assigned patients" value={data?.counts?.assigned_patients || 0} />
          <StatCard label="High risk" value={data?.counts?.high_risk || 0} />
          <StatCard label="Appointments" value={data?.counts?.appointments || 0} />
          <StatCard label="Clinical notes" value={data?.counts?.notes || 0} />
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <div className="space-y-4 xl:col-span-2">
            <SectionCard title="Patient clinical review" subtitle="Risk, relapse forecast, medication adherence, and latest log in one doctor view.">
              <div className="grid gap-3 md:grid-cols-2">
                {(data?.patients || []).length === 0 ? <p className="text-sm text-slate-500">No patients available.</p> : data.patients.map((item) => (
                  <button key={item.patient.id} onClick={() => setSelectedPatient(String(item.patient.id))} className={`rounded-2xl border p-4 text-left shadow-sm ${selectedPatient === String(item.patient.id) ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white"}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-lg font-semibold text-slate-900">{item.user?.full_name || `Patient ${item.patient.id}`}</p>
                        <p className="text-sm text-slate-500">{item.patient.diagnosis}</p>
                      </div>
                      <AlertBadge level={item.risk?.risk_level} />
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-sm text-slate-600">
                      <div className="rounded-xl bg-slate-50 p-2">Risk {item.risk?.risk_score ?? 0}</div>
                      <div className="rounded-xl bg-slate-50 p-2">Relapse {item.prediction?.probability ?? 0}%</div>
                      <div className="rounded-xl bg-slate-50 p-2">Meds {item.adherence?.adherence_score ?? 0}%</div>
                    </div>
                    <p className="mt-3 text-sm text-slate-600">{item.prediction?.trend}</p>
                  </button>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Clinical notes">
              <div className="space-y-3">
                {(data?.notes || []).length === 0 ? <p className="text-sm text-slate-500">No notes yet.</p> : data.notes.map((item) => (
                  <div key={item.id} className="rounded-2xl bg-slate-50 p-4 text-sm">
                    <p className="font-semibold text-slate-900">{item.note_type} - Patient #{item.patient_id}</p>
                    <p className="mt-1 text-slate-700">{item.summary}</p>
                    {item.prescription ? <p className="mt-2 text-slate-500">Prescription: {item.prescription}</p> : null}
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

          <div className="space-y-4">
            <SectionCard title="Create doctor note">
              <div className="space-y-3">
                <select className="w-full rounded-2xl border border-slate-200 p-3" value={selectedPatient} onChange={(e) => setSelectedPatient(e.target.value)}>
                  {(data?.patients || []).map((item) => <option key={item.patient.id} value={item.patient.id}>{item.user?.full_name || `Patient ${item.patient.id}`}</option>)}
                </select>
                <input className="w-full rounded-2xl border border-slate-200 p-3" value={note.note_type} onChange={(e) => setNote((p) => ({ ...p, note_type: e.target.value }))} />
                <textarea className="w-full rounded-2xl border border-slate-200 p-3" rows="5" placeholder="Consultation summary" value={note.summary} onChange={(e) => setNote((p) => ({ ...p, summary: e.target.value }))} />
                <textarea className="w-full rounded-2xl border border-slate-200 p-3" rows="3" placeholder="Prescription notes" value={note.prescription} onChange={(e) => setNote((p) => ({ ...p, prescription: e.target.value }))} />
                <input type="date" className="w-full rounded-2xl border border-slate-200 p-3" value={note.follow_up_date} onChange={(e) => setNote((p) => ({ ...p, follow_up_date: e.target.value }))} />
                <button onClick={saveNote} className="w-full rounded-2xl bg-slate-900 py-3 text-white">Save note</button>
              </div>
            </SectionCard>

            <SectionCard title="Appointment scheduling">
              <div className="space-y-3">
                <input type="datetime-local" className="w-full rounded-2xl border border-slate-200 p-3" value={appointment.scheduled_at} onChange={(e) => setAppointment((p) => ({ ...p, scheduled_at: e.target.value }))} />
                <input className="w-full rounded-2xl border border-slate-200 p-3" placeholder="Reason" value={appointment.reason} onChange={(e) => setAppointment((p) => ({ ...p, reason: e.target.value }))} />
                <textarea className="w-full rounded-2xl border border-slate-200 p-3" rows="3" placeholder="Notes" value={appointment.notes} onChange={(e) => setAppointment((p) => ({ ...p, notes: e.target.value }))} />
                <button onClick={scheduleAppointment} className="w-full rounded-2xl bg-emerald-600 py-3 text-white">Schedule</button>
              </div>
            </SectionCard>

            <SectionCard title="Upcoming appointments">
              <div className="space-y-3 text-sm">
                {(data?.appointments || []).length === 0 ? <p className="text-slate-500">No appointments yet.</p> : data.appointments.map((item) => (
                  <div key={item.id} className="rounded-2xl bg-slate-50 p-3">
                    <p className="font-semibold text-slate-900">Patient #{item.patient_id}</p>
                    <p className="text-slate-600">{new Date(item.scheduled_at).toLocaleString()}</p>
                    <p className="text-slate-500">{item.reason}</p>
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
