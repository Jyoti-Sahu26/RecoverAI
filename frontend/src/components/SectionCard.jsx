export default function SectionCard({ title, subtitle, children, action }) {
  return (
    <section className="group relative overflow-hidden rounded-3xl border border-white/70 bg-white/85 p-5 shadow-[0_22px_55px_rgba(15,23,42,0.10)] backdrop-blur-xl transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_28px_70px_rgba(15,118,110,0.16)]">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 via-sky-400 to-fuchsia-400" />
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-950">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm leading-6 text-slate-500">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
