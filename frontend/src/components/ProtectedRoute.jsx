import { Navigate, useLocation, useParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute({ children, role }) {
  const { booting, isAuthenticated, role: currentRole, session } = useAuth();
  const location = useLocation();
  const params = useParams();

  if (booting) {
    return <div className="panel p-8 text-center text-ink/60">Restoring session...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location }} />;
  }

  if (role && currentRole !== role) {
    return <Navigate to="/" replace />;
  }

  if (role === "worker" && params.workerId && session?.session?.worker_id !== params.workerId) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
