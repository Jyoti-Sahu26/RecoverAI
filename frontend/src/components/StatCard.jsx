export default function StatCard({ label, value, hint }) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/70 bg-white/85 p-4 shadow-[0_18px_45px_rgba(15,23,42,0.09)] backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:border-emerald-200 hover:shadow-[0_24px_60px_rgba(14,165,233,0.16)]">
      <div className="absolute right-0 top-0 h-12 w-24 bg-gradient-to-l from-emerald-100 via-sky-100 to-transparent" />
      <p className="relative text-sm font-medium text-slate-500">{label}</p>
      <p className="relative mt-2 text-3xl font-extrabold tracking-tight text-slate-950">{value}</p>
      {hint ? <p className="relative mt-2 text-xs leading-5 text-slate-500">{hint}</p> : null}
    </div>
  );
}
