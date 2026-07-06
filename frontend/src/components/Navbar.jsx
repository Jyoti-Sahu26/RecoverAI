import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Navbar({ title }) {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const navigate = useNavigate();
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  const [fontSize, setFontSize] = useState(localStorage.getItem("fontSize") || "standard");
  const [openMenu, setOpenMenu] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.dataset.fontSize = fontSize;
    localStorage.setItem("fontSize", fontSize);
  }, [fontSize]);

  const workspaceLinks = useMemo(() => {
    if (user?.role === "patient") {
      return [
        { label: "Dashboard", to: "/patient" },
        { label: "Daily Log", to: "/checkin" },
        { label: "AI Health Center", to: "/ai-health" },
        { label: "Advanced Recovery Hub", to: "/advanced" },
        { label: "Onboarding", to: "/onboarding" },
      ];
    }
    if (user?.role === "caregiver") return [{ label: "Caregiver Dashboard", to: "/caregiver" }];
    if (user?.role === "doctor") return [{ label: "Doctor Portal", to: "/doctor" }];
    if (user?.role === "admin") return [{ label: "Admin Dashboard", to: "/admin" }];
    return [];
  }, [user?.role]);

  const initials = (user?.full_name || "U")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const toggleMenu = (menu) => {
    setOpenMenu((current) => (current === menu ? "" : menu));
  };

  const showMenu = (menu) => setOpenMenu(menu);
  const closeMenus = () => setOpenMenu("");

  const logout = () => {
    localStorage.removeItem("user");
    closeMenus();
    navigate("/login");
  };

  const menuPanel = "absolute right-0 top-full z-[100] mt-3 w-64 rounded-2xl border border-white/70 bg-white/95 p-2 shadow-[0_24px_70px_rgba(15,23,42,0.22)] backdrop-blur-xl";
  const menuLink = "block rounded-xl px-3 py-2 text-left text-sm text-slate-700 transition hover:bg-gradient-to-r hover:from-emerald-50 hover:to-sky-50 hover:text-emerald-800";
  const navButton = "rounded-full px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:shadow-md";

  return (
    <div className="relative z-[80] overflow-visible rounded-3xl border border-white/70 bg-white/85 p-4 shadow-[0_22px_60px_rgba(15,23,42,0.12)] backdrop-blur-xl">
      <div className="absolute inset-x-6 top-0 h-1 rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-fuchsia-400" />
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.36em] text-emerald-700">RecoverAI</p>
          <h1 className="text-3xl font-black tracking-tight text-slate-950">{title}</h1>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm">
          {user ? <Link onClick={closeMenus} className={`${navButton} bg-slate-900 text-white hover:bg-emerald-700`} to="/home">Home</Link> : null}

          {workspaceLinks.length > 0 ? (
            <div className="group relative" onMouseEnter={() => showMenu("care")} onMouseLeave={closeMenus}>
              <button type="button" className={`${navButton} bg-slate-200 text-slate-800 hover:bg-emerald-100 hover:text-emerald-900`} onClick={() => toggleMenu("care")}>
                Care Hub
              </button>
              <div className={`${menuPanel} ${openMenu === "care" ? "block" : "hidden group-hover:block"}`}>
                <p className="px-3 py-2 text-xs font-semibold uppercase text-slate-500">Patient tools</p>
                {workspaceLinks.map((item) => (
                  <Link key={item.to} onClick={closeMenus} className={menuLink} to={item.to}>{item.label}</Link>
                ))}
              </div>
            </div>
          ) : null}

          <div className="group relative" onMouseEnter={() => showMenu("display")} onMouseLeave={closeMenus}>
            <button type="button" className={`${navButton} bg-slate-100 text-slate-700 hover:bg-sky-100 hover:text-sky-900`} onClick={() => toggleMenu("display")}>
              Display
            </button>
            <div className={`${menuPanel} ${openMenu === "display" ? "block" : "hidden group-hover:block"}`}>
              <label className="block px-3 py-2 text-xs font-semibold uppercase text-slate-500">Theme</label>
              <select className="mb-3 w-full rounded-xl border border-slate-200 p-2 text-sm transition hover:border-sky-300 hover:bg-sky-50" value={theme} onChange={(event) => setTheme(event.target.value)}>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
              <label className="block px-3 py-2 text-xs font-semibold uppercase text-slate-500">Text size</label>
              <select className="w-full rounded-xl border border-slate-200 p-2 text-sm transition hover:border-emerald-300 hover:bg-emerald-50" value={fontSize} onChange={(event) => setFontSize(event.target.value)}>
                <option value="standard">A</option>
                <option value="large">A+</option>
              </select>
            </div>
          </div>

          {user ? (
            <div className="group relative" onMouseEnter={() => showMenu("profile")} onMouseLeave={closeMenus}>
              <button type="button" className="flex max-w-56 items-center gap-2 rounded-full bg-emerald-50 px-3 py-2 font-semibold text-emerald-900 transition hover:-translate-y-0.5 hover:bg-gradient-to-r hover:from-emerald-100 hover:to-cyan-100 hover:shadow-md" onClick={() => toggleMenu("profile")}>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-xs font-bold text-white">{initials}</span>
                <span className="truncate">{user.full_name}</span>
              </button>
              <div className={`${menuPanel} ${openMenu === "profile" ? "block" : "hidden group-hover:block"}`}>
                <div className="rounded-xl bg-slate-50 p-3 text-sm">
                  <p className="font-semibold text-slate-900">{user.full_name}</p>
                  <p className="break-all text-slate-500">{user.email}</p>
                  <p className="mt-1 text-xs uppercase text-slate-500">{user.role}</p>
                </div>
                <button type="button" className="mt-2 w-full rounded-xl bg-rose-100 px-3 py-2 text-left text-sm font-semibold text-rose-700 transition hover:bg-gradient-to-r hover:from-rose-100 hover:to-orange-100 hover:text-rose-800" onClick={logout}>
                  Logout
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
