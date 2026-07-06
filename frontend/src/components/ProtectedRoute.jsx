import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ allowedRole, children }) {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRole && user.role !== allowedRole) return <Navigate to="/home" replace />;
  return children;
}
