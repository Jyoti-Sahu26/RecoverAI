import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";

export default function Login() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    try {
      setLoading(true);
      setMessage("");
      const res = await api.post("/auth/login", form);
      localStorage.setItem("user", JSON.stringify(res.data));
      navigate("/home");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#dbeafe,_#f8fafc_40%,_#ecfeff_100%)] p-4">
      <div className="w-full max-w-md rounded-[2rem] border border-white/40 bg-white/75 p-6 shadow-2xl backdrop-blur-xl">
        <h1 className="text-3xl font-bold text-slate-900">RecoverAI</h1>
        <p className="mt-2 text-sm text-slate-500">Login, go to the homepage, then continue your role-based flow.</p>
        {message ? <div className="mt-4 rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">{message}</div> : null}
        <div className="mt-5 space-y-3">
          <input className="w-full rounded-2xl border border-slate-200 bg-white p-3" placeholder="Email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} />
          <input type="password" className="w-full rounded-2xl border border-slate-200 bg-white p-3" placeholder="Password" value={form.password} onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} />
          <button onClick={handleLogin} disabled={loading} className="w-full rounded-2xl bg-slate-900 py-3 text-white disabled:opacity-50">{loading ? "Signing in..." : "Login"}</button>
        </div>
        <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
          <Link className="font-semibold text-blue-600" to="/register">Register with OTP</Link>
          <Link className="font-semibold text-blue-600" to="/reset-password">Reset password</Link>
        </div>
      </div>
    </div>
  );
}
