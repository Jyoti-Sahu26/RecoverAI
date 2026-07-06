import { Navigate, useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import SectionCard from "../components/SectionCard";

const accents = [
  {
    band: "from-emerald-500 via-teal-500 to-sky-500",
    tint: "from-emerald-50 to-sky-50",
    text: "text-emerald-700",
  },
  {
    band: "from-sky-500 via-cyan-500 to-indigo-500",
    tint: "from-sky-50 to-indigo-50",
    text: "text-sky-700",
  },
  {
    band: "from-rose-500 via-orange-400 to-amber-400",
    tint: "from-rose-50 to-amber-50",
    text: "text-rose-700",
  },
  {
    band: "from-violet-500 via-fuchsia-500 to-rose-500",
    tint: "from-violet-50 to-rose-50",
    text: "text-violet-700",
  },
];

export default function HomePage() {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const navigate = useNavigate();

  if (!user) return <Navigate to="/login" replace />;

  const cards = {
    patient: [
      { title: "Patient dashboard", label: "Monitor", text: "Latest risk score, recovery plan, graph, notifications, and clinical trend summary.", action: () => navigate("/patient") },
      { title: "AI Health Center", label: "AI", text: "Chatbot, relapse prediction, XAI insights, SOS, wearables, reports, voice, and mood tools.", action: () => navigate("/ai-health") },
      { title: "Advanced Recovery Hub", label: "Twin", text: "Digital twin, recovery score, heatmap, OCR, meal planner, vault, community, and simulations.", action: () => navigate("/advanced") },
      { title: "Onboarding", label: "Profile", text: "Set diagnosis, caregiver, doctor, emergency contact, accessibility, medicines, and goals.", action: () => navigate("/onboarding") },
      { title: "Daily symptom log", label: "Log", text: "Record symptoms once per day and store explainable risk results automatically.", action: () => navigate("/checkin") },
    ],
    caregiver: [
      { title: "Caregiver dashboard", label: "Care", text: "Track linked patients, risk alerts, emergency updates, and missed alert reminders.", action: () => navigate("/caregiver") },
    ],
    doctor: [
      { title: "Doctor portal", label: "Clinical", text: "Review assigned patients, relapse forecasts, notes, prescriptions, and appointments.", action: () => navigate("/doctor") },
    ],
    admin: [
      { title: "Admin dashboard", label: "Operations", text: "Monitor users, alerts, logs, system analytics, notifications, and recovery KPIs.", action: () => navigate("/admin") },
    ],
  };

  const activeCards = cards[user.role] || [];

  return (
    <div className="min-h-screen p-4">
      <div className="mx-auto max-w-7xl space-y-5">
        <Navbar title="Homepage" />

        <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-slate-950 p-6 text-white shadow-[0_30px_90px_rgba(15,23,42,0.28)]">
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 via-cyan-400 to-fuchsia-400" />
          <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(16,185,129,0.16),transparent_32%,rgba(14,165,233,0.14)_58%,rgba(217,70,239,0.12))]" />
          <div className="relative grid gap-6 lg:grid-cols-[1.3fr_0.7fr] lg:items-end">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-emerald-200">AI Recovery Command Center</p>
              <h2 className="mt-4 max-w-3xl text-4xl font-black tracking-tight md:text-5xl">RecoverAI feels ready for real patient recovery workflows.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200">
                Welcome back, {user.full_name}. Your workspace brings monitoring, prediction, clinical escalation, and recovery engagement into one polished healthcare hub.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              {[
                ["Role", user.role],
                ["Workspace", activeCards.length],
                ["Mode", "Predictive"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-300">{label}</p>
                  <p className="mt-2 text-2xl font-extrabold capitalize">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <SectionCard title="Your care workspace" subtitle="Choose the next action from your role-based flow.">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {activeCards.map((card, index) => {
              const accent = accents[index % accents.length];
              return (
                <button
                  key={card.title}
                  onClick={card.action}
                  className={`group relative overflow-hidden rounded-3xl border border-white/80 bg-gradient-to-br ${accent.tint} p-5 text-left shadow-[0_18px_45px_rgba(15,23,42,0.08)] transition duration-300 hover:-translate-y-1.5 hover:shadow-[0_28px_70px_rgba(15,118,110,0.18)]`}
                >
                  <div className={`absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r ${accent.band}`} />
                  <div className={`inline-flex rounded-full bg-white/75 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] ${accent.text}`}>
                    {card.label}
                  </div>
                  <h3 className="mt-5 text-xl font-black tracking-tight text-slate-950">{card.title}</h3>
                  <p className="mt-3 min-h-20 text-sm leading-6 text-slate-600">{card.text}</p>
                  <div className="mt-5 flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-900">Open</span>
                    <span className={`flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-r ${accent.band} text-lg font-bold text-white shadow-lg transition group-hover:translate-x-1`}>
                      &gt;
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
