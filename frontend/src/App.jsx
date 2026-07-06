import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminDashboard from "./pages/AdminDashboard";
import AdvancedRecoveryHub from "./pages/AdvancedRecoveryHub";
import AIHealthCenter from "./pages/AIHealthCenter";
import CaregiverDashboard from "./pages/CaregiverDashboard";
import DailyCheckIn from "./pages/DailyCheckIn";
import DoctorDashboard from "./pages/DoctorDashboard";
import HomePage from "./pages/HomePage";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import PatientDashboard from "./pages/PatientDashboard";
import Register from "./pages/Register";
import ResetPassword from "./pages/ResetPassword";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
        <Route path="/patient" element={<ProtectedRoute allowedRole="patient"><PatientDashboard /></ProtectedRoute>} />
        <Route path="/onboarding" element={<ProtectedRoute allowedRole="patient"><Onboarding /></ProtectedRoute>} />
        <Route path="/checkin" element={<ProtectedRoute allowedRole="patient"><DailyCheckIn /></ProtectedRoute>} />
        <Route path="/ai-health" element={<ProtectedRoute allowedRole="patient"><AIHealthCenter /></ProtectedRoute>} />
        <Route path="/advanced" element={<ProtectedRoute allowedRole="patient"><AdvancedRecoveryHub /></ProtectedRoute>} />
        <Route path="/caregiver" element={<ProtectedRoute allowedRole="caregiver"><CaregiverDashboard /></ProtectedRoute>} />
        <Route path="/doctor" element={<ProtectedRoute allowedRole="doctor"><DoctorDashboard /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute allowedRole="admin"><AdminDashboard /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
