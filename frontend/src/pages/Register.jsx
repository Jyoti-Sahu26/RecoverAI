import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";

const initialForm = {
  full_name: "",
  email: "",
  password: "",
  role: "patient",
  phone: "",
  otp_code: "",
};

function extractErrorMessage(error) {
  if (error?.code === "ERR_NETWORK" || !error?.response) {
    return "Cannot reach backend server. Start FastAPI on http://127.0.0.1:8000, then try again.";
  }
  if (error?.code === "ECONNABORTED") {
    return "Backend request timed out. Check that FastAPI is still running on port 8000.";
  }
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }
  return "Something went wrong. Please try again.";
}

export default function Register() {
  const [form, setForm] = useState(initialForm);
  const [otpSent, setOtpSent] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const canRequestOtp = useMemo(() => {
    return form.full_name.trim().length >= 2 &&
      /\S+@\S+\.\S+/.test(form.email) &&
      form.password.length >= 6 &&
      ["patient", "caregiver", "doctor", "admin"].includes(form.role);
  }, [form]);

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const requestOtp = async () => {
    if (!canRequestOtp) {
      setError("Enter full name, valid email, password of at least 6 characters, and role.");
      setMessage("");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");

      const payload = {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        role: form.role.toLowerCase(),
        phone: form.phone.trim() || null,
      };

      await api.post("/auth/request-otp", payload);
      setOtpSent(true);
      setMessage(`OTP sent to ${payload.email}. Check that email inbox and enter the code below.`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const verifyAndRegister = async () => {
    if (!form.otp_code.trim()) {
      setError("Enter the OTP sent to your email.");
      setMessage("");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");

      await api.post("/auth/verify-otp-register", {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        role: form.role.toLowerCase(),
        phone: form.phone.trim() || null,
        otp_code: form.otp_code.trim(),
      });

      setMessage("Registration complete. Redirecting to login...");
      setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#dcfce7,_#f8fafc_45%,_#dbeafe_100%)] p-4">
      <div className="w-full max-w-xl rounded-[2rem] border border-white/40 bg-white/85 p-6 shadow-2xl backdrop-blur-xl">
        <h1 className="text-3xl font-bold text-slate-900">OTP Registration</h1>
        <p className="mt-2 text-sm text-slate-500">Register once, verify with OTP, then login to your own account.</p>

        {message ? <div className="mt-4 rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div> : null}
        {error ? <div className="mt-4 rounded-2xl bg-rose-50 p-3 text-sm text-rose-700">{error}</div> : null}
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <input
            className="rounded-2xl border border-slate-200 p-3 outline-none ring-0 focus:border-emerald-400"
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => updateField("full_name", e.target.value)}
          />
          <input
            className="rounded-2xl border border-slate-200 p-3 outline-none ring-0 focus:border-emerald-400"
            placeholder="Phone (optional)"
            value={form.phone}
            onChange={(e) => updateField("phone", e.target.value)}
          />
          <input
            type="email"
            className="rounded-2xl border border-slate-200 p-3 outline-none ring-0 focus:border-emerald-400 md:col-span-2"
            placeholder="Email"
            value={form.email}
            onChange={(e) => updateField("email", e.target.value)}
          />
          <input
            type="password"
            className="rounded-2xl border border-slate-200 p-3 outline-none ring-0 focus:border-emerald-400"
            placeholder="Password (min 6 characters)"
            value={form.password}
            onChange={(e) => updateField("password", e.target.value)}
          />
          <select
            className="rounded-2xl border border-slate-200 p-3 outline-none ring-0 focus:border-emerald-400"
            value={form.role}
            onChange={(e) => updateField("role", e.target.value)}
          >
            <option value="patient">Patient</option>
            <option value="caregiver">Caregiver</option>
            <option value="doctor">Doctor</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {!otpSent ? (
          <button
            onClick={requestOtp}
            disabled={loading}
            className="mt-5 w-full rounded-2xl bg-slate-900 py-3 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Generating OTP..." : "Send OTP"}
          </button>
        ) : (
          <>
            <input
              className="mt-5 w-full rounded-2xl border border-slate-200 p-3 outline-none ring-0 focus:border-emerald-400"
              placeholder="Enter OTP"
              value={form.otp_code}
              onChange={(e) => updateField("otp_code", e.target.value)}
            />
            <button
              onClick={verifyAndRegister}
              disabled={loading}
              className="mt-3 w-full rounded-2xl bg-emerald-600 py-3 text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Verifying..." : "Verify OTP and Register"}
            </button>
          </>
        )}

        <p className="mt-4 text-sm text-slate-600">
          Already registered? <Link className="font-semibold text-blue-600" to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}
