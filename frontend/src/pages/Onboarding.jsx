import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import SectionCard from "../components/SectionCard";
import api from "../services/api";

const medTemplate = { medicine_name: "", dosage: "", timing: "", instructions: "" };

export default function Onboarding() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [caregivers, setCaregivers] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [form, setForm] = useState({
    age: 30,
    gender: "Female",
    diagnosis: "Post-surgery recovery",
    surgery_type: "Orthopedic",
    discharge_date: new Date().toISOString().split("T")[0],
    caregiver_id: "",
    doctor_id: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    location_consent: false,
    health_goal: "",
    preferred_language: "English",
    accessibility_mode: "standard",
    comorbidities: "",
    notes: "",
    target_sleep_hours: 8,
    target_steps: 2500,
    reminder_time: "20:00",
    medications: [medTemplate],
  });

  useEffect(() => {
    const loadCaregivers = async () => {
      try {
        const res = await api.get("/patients/caregivers/options");
        setCaregivers(res.data || []);
      } catch {
        setCaregivers([]);
      }
    };
    const loadDoctors = async () => {
      try {
        const res = await api.get("/doctors/options");
        setDoctors(res.data || []);
      } catch {
        setDoctors([]);
      }
    };
    loadCaregivers();
    loadDoctors();
  }, []);

  const updateMed = (index, key, value) => {
    const copy = [...form.medications];
    copy[index] = { ...copy[index], [key]: value };
    setForm((prev) => ({ ...prev, medications: copy }));
  };

  const addMed = () => setForm((prev) => ({ ...prev, medications: [...prev.medications, { ...medTemplate }] }));

  const submit = async () => {
    try {
      setLoading(true);
      setMessage("");
      await api.post(`/patients/onboard/${user.user_id}`, {
        ...form,
        caregiver_id: form.caregiver_id ? Number(form.caregiver_id) : null,
        doctor_id: form.doctor_id ? Number(form.doctor_id) : null,
        target_sleep_hours: Number(form.target_sleep_hours),
        target_steps: Number(form.target_steps),
        comorbidities: form.comorbidities.split(",").map((item) => item.trim()).filter(Boolean),
      });
      navigate("/patient");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Onboarding failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#dcfce7,_#f8fafc_40%,_#dbeafe_100%)] p-4">
      <div className="mx-auto max-w-5xl space-y-4">
        <Navbar title="Patient Onboarding" />
        {message ? <div className="rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">{message}</div> : null}

        <SectionCard title="Profile setup" subtitle="This creates the patient profile and recovery plan.">
          <div className="grid gap-4 md:grid-cols-2">
            <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Age" value={form.age} onChange={(e) => setForm((prev) => ({ ...prev, age: e.target.value }))} />
            <input type="text" className="rounded-2xl border border-slate-200 p-3" placeholder="Gender" value={form.gender} onChange={(e) => setForm((prev) => ({ ...prev, gender: e.target.value }))} />
            <input type="text" className="rounded-2xl border border-slate-200 p-3" placeholder="Diagnosis" value={form.diagnosis} onChange={(e) => setForm((prev) => ({ ...prev, diagnosis: e.target.value }))} />
            <input type="text" className="rounded-2xl border border-slate-200 p-3" placeholder="Surgery type" value={form.surgery_type} onChange={(e) => setForm((prev) => ({ ...prev, surgery_type: e.target.value }))} />
            <input type="date" className="rounded-2xl border border-slate-200 p-3" value={form.discharge_date} onChange={(e) => setForm((prev) => ({ ...prev, discharge_date: e.target.value }))} />
            <select className="rounded-2xl border border-slate-200 p-3" value={form.caregiver_id} onChange={(e) => setForm((prev) => ({ ...prev, caregiver_id: e.target.value }))}>
              <option value="">Assign caregiver</option>
              {caregivers.map((caregiver) => <option key={caregiver.id} value={caregiver.id}>{caregiver.full_name} ({caregiver.email})</option>)}
            </select>
            <select className="rounded-2xl border border-slate-200 p-3" value={form.doctor_id} onChange={(e) => setForm((prev) => ({ ...prev, doctor_id: e.target.value }))}>
              <option value="">Assign doctor</option>
              {doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>{doctor.full_name} ({doctor.email})</option>)}
            </select>
            <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Target sleep hours" value={form.target_sleep_hours} onChange={(e) => setForm((prev) => ({ ...prev, target_sleep_hours: e.target.value }))} />
            <input type="number" className="rounded-2xl border border-slate-200 p-3" placeholder="Target steps" value={form.target_steps} onChange={(e) => setForm((prev) => ({ ...prev, target_steps: e.target.value }))} />
            <input type="time" className="rounded-2xl border border-slate-200 p-3" value={form.reminder_time} onChange={(e) => setForm((prev) => ({ ...prev, reminder_time: e.target.value }))} />
            <input className="rounded-2xl border border-slate-200 p-3" placeholder="Emergency contact name" value={form.emergency_contact_name} onChange={(e) => setForm((prev) => ({ ...prev, emergency_contact_name: e.target.value }))} />
            <input className="rounded-2xl border border-slate-200 p-3" placeholder="Emergency contact phone" value={form.emergency_contact_phone} onChange={(e) => setForm((prev) => ({ ...prev, emergency_contact_phone: e.target.value }))} />
            <select className="rounded-2xl border border-slate-200 p-3" value={form.preferred_language} onChange={(e) => setForm((prev) => ({ ...prev, preferred_language: e.target.value }))}>
              <option>English</option>
              <option>Hindi</option>
              <option>Marathi</option>
              <option>Odia</option>
            </select>
            <select className="rounded-2xl border border-slate-200 p-3" value={form.accessibility_mode} onChange={(e) => setForm((prev) => ({ ...prev, accessibility_mode: e.target.value }))}>
              <option value="standard">Standard accessibility</option>
              <option value="large_text">Large text</option>
              <option value="high_contrast">High contrast</option>
              <option value="voice_first">Voice first</option>
            </select>
            <label className="rounded-2xl border border-slate-200 p-3 text-sm text-slate-700">
              <input type="checkbox" className="mr-2" checked={form.location_consent} onChange={(e) => setForm((prev) => ({ ...prev, location_consent: e.target.checked }))} />
              Allow location sharing during SOS
            </label>
            <input className="rounded-2xl border border-slate-200 p-3 md:col-span-2" placeholder="Comorbidities (comma separated)" value={form.comorbidities} onChange={(e) => setForm((prev) => ({ ...prev, comorbidities: e.target.value }))} />
            <textarea className="rounded-2xl border border-slate-200 p-3 md:col-span-2" rows="3" placeholder="Recovery goal" value={form.health_goal} onChange={(e) => setForm((prev) => ({ ...prev, health_goal: e.target.value }))} />
            <textarea className="rounded-2xl border border-slate-200 p-3 md:col-span-2" rows="4" placeholder="Notes" value={form.notes} onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))} />
          </div>
        </SectionCard>

        <SectionCard title="Medication setup" action={<button type="button" onClick={addMed} className="rounded-full bg-slate-900 px-4 py-2 text-sm text-white">Add medicine</button>}>
          <div className="space-y-3">
            {form.medications.map((med, index) => (
              <div key={index} className="grid gap-3 md:grid-cols-4">
                <input className="rounded-2xl border border-slate-200 p-3" placeholder="Medicine" value={med.medicine_name} onChange={(e) => updateMed(index, "medicine_name", e.target.value)} />
                <input className="rounded-2xl border border-slate-200 p-3" placeholder="Dosage" value={med.dosage} onChange={(e) => updateMed(index, "dosage", e.target.value)} />
                <input className="rounded-2xl border border-slate-200 p-3" placeholder="Timing" value={med.timing} onChange={(e) => updateMed(index, "timing", e.target.value)} />
                <input className="rounded-2xl border border-slate-200 p-3" placeholder="Instructions" value={med.instructions} onChange={(e) => updateMed(index, "instructions", e.target.value)} />
              </div>
            ))}
          </div>
        </SectionCard>

        <button onClick={submit} disabled={loading} className="w-full rounded-2xl bg-emerald-600 py-3 text-white disabled:opacity-50">{loading ? "Saving..." : "Complete onboarding"}</button>
      </div>
    </div>
  );
}
