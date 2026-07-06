import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

export default function ResetPassword() {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [requested, setRequested] = useState(false);
  const [message, setMessage] = useState("");

  const requestOtp = async () => {
    try {
      await api.post("/auth/request-password-reset", { email });
      setRequested(true);
      setMessage(`Password reset OTP sent to ${email}.`);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to send OTP");
    }
  };

  const resetPassword = async () => {
    try {
      await api.post("/auth/reset-password", { email, otp_code: otp, new_password: newPassword });
      setMessage("Password reset successful. You can login now.");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to reset password");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#fee2e2,_#f8fafc_45%,_#dbeafe_100%)] p-4">
      <div className="w-full max-w-md rounded-[2rem] border border-white/40 bg-white/80 p-6 shadow-2xl backdrop-blur-xl">
        <h1 className="text-2xl font-bold text-slate-900">Reset password via OTP</h1>
        {message ? <div className="mt-4 rounded-2xl bg-slate-100 p-3 text-sm text-slate-700">{message}</div> : null}
        <input className="mt-5 w-full rounded-2xl border border-slate-200 p-3" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        {!requested ? (
          <button onClick={requestOtp} className="mt-4 w-full rounded-2xl bg-slate-900 py-3 text-white">Send reset OTP</button>
        ) : (
          <>
            <input className="mt-4 w-full rounded-2xl border border-slate-200 p-3" placeholder="OTP" value={otp} onChange={(e) => setOtp(e.target.value)} />
            <input type="password" className="mt-4 w-full rounded-2xl border border-slate-200 p-3" placeholder="New password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            <button onClick={resetPassword} className="mt-4 w-full rounded-2xl bg-emerald-600 py-3 text-white">Reset password</button>
          </>
        )}
        <p className="mt-4 text-sm text-slate-600"><Link className="font-semibold text-blue-600" to="/login">Back to login</Link></p>
      </div>
    </div>
  );
}
