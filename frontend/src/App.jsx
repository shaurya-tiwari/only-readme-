import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

const Auth = lazy(() => import("./pages/Auth"));
const Home = lazy(() => import("./pages/Home"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const AdminPanel = lazy(() => import("./pages/AdminPanel"));
const DemoRunner = lazy(() => import("./pages/DemoRunner"));

function RedirectIfAuth({ children }) {
  const { booting, isAuthenticated, role } = useAuth();

  if (booting) {
    return <div className="panel p-8 text-center text-ink/60">Restoring session...</div>;
  }

  if (!isAuthenticated) {
    return children;
  }

  if (role === "admin") {
    return <Navigate to="/admin" replace />;
  }

  if (role === "worker") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppShell() {
  const { session } = useAuth();

  return (
    <div className="min-h-screen bg-mesh-paper text-ink">
      <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
        <Navbar session={session?.session} />
        <Suspense fallback={<div className="panel p-8 text-center text-ink/60">Loading page...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route
              path="/auth"
              element={(
                <RedirectIfAuth>
                  <Auth />
                </RedirectIfAuth>
              )}
            />
            <Route
              path="/onboarding"
              element={(
                <RedirectIfAuth>
                  <Onboarding />
                </RedirectIfAuth>
              )}
            />
            <Route
              path="/dashboard"
              element={(
                <ProtectedRoute role="worker">
                  <Dashboard />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/dashboard/:workerId"
              element={(
                <ProtectedRoute role="worker">
                  <Dashboard />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/admin"
              element={(
                <ProtectedRoute role="admin">
                  <AdminPanel />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/demo"
              element={(
                <ProtectedRoute role="admin">
                  <DemoRunner />
                </ProtectedRoute>
              )}
            />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
