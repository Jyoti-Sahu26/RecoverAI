export default function NotificationList({ items = [] }) {
  if (!items.length) return <p className="text-sm text-slate-500">No notifications yet.</p>;
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.id} className="rounded-2xl bg-slate-50 p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <p className="font-semibold text-slate-900">{item.title}</p>
            <span className={`rounded-full px-2 py-1 text-xs ${item.read ? "bg-slate-200 text-slate-600" : "bg-blue-100 text-blue-700"}`}>
              {item.read ? "Read" : "New"}
            </span>
          </div>
          <p className="mt-1 text-slate-600">{item.message}</p>
        </div>
      ))}
    </div>
  );
}
