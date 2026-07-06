const styles = {
  low: "bg-emerald-100 text-emerald-700",
  moderate: "bg-amber-100 text-amber-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-rose-100 text-rose-700",
  unknown: "bg-slate-100 text-slate-700",
};

export default function AlertBadge({ level = "unknown" }) {
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${styles[level] || styles.unknown}`}>{level}</span>;
}
