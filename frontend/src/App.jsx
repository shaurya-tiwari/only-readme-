import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppFrame from "./components/AppFrame";
import ErrorBoundary from "./components/ErrorBoundary";
import ProtectedRoute from "./components/ProtectedRoute";
import PublicShell from "./components/PublicShell";
import WhatsAppFloatingButton from "./components/WhatsAppFloatingButton";

const Auth = lazy(() => import("./pages/Auth"));
const Home = lazy(() => import("./pages/Home"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const IntelligenceOverview = lazy(() => import("./pages/IntelligenceOverview"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const AdminPanel = lazy(() => import("./pages/AdminPanel"));
const DemoRunner = lazy(() => import("./pages/DemoRunner"));
const ScenarioLab = lazy(() => import("./pages/ScenarioLab"));

function RedirectIfAuth({ children }) {
  const { booting, isAuthenticated, role } = useAuth();

  if (booting) {
    return <div className="panel p-8 text-center text-on-surface-variant">Restoring session...</div>;
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
  return (
    <div className="min-h-screen text-ink">
      <Suspense fallback={<div className="panel m-6 p-8 text-center text-on-surface-variant">Loading page...</div>}>
        <Routes>
          {/* Public routes — all share PublicShell (navbar + max-width container) */}
          <Route path="/" element={<PublicShell><Home /></PublicShell>} />

          <Route path="/how-it-works" element={<PublicShell><HowItWorks /></PublicShell>} />

          <Route
            path="/auth"
            element={
              <PublicShell>
                <RedirectIfAuth>
                  <Auth />
                </RedirectIfAuth>
              </PublicShell>
            }
          />

          <Route
            path="/onboarding"
            element={
              <PublicShell>
                <RedirectIfAuth>
                  <Onboarding />
                </RedirectIfAuth>
              </PublicShell>
            }
          />

          {/* Protected routes — AppFrame provides sidebar + header */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute role="worker">
                <AppFrame>
                  <Dashboard />
                </AppFrame>
              </ProtectedRoute>
            }
          />

          <Route
            path="/dashboard/:workerId"
            element={
              <ProtectedRoute role="worker">
                <AppFrame>
                  <Dashboard />
                </AppFrame>
              </ProtectedRoute>
            }
          />

          <Route
            path="/intelligence"
            element={
              <ProtectedRoute role="admin">
                <AppFrame>
                  <IntelligenceOverview />
                </AppFrame>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedRoute role="admin">
                <AppFrame>
                  <AdminPanel />
                </AppFrame>
              </ProtectedRoute>
            }
          />

          <Route
            path="/demo"
            element={
              <ProtectedRoute role="admin">
                <AppFrame>
                  <DemoRunner />
                </AppFrame>
              </ProtectedRoute>
            }
          />

          <Route
            path="/lab"
            element={
              <ProtectedRoute role="admin">
                <AppFrame>
                  <ScenarioLab />
                </AppFrame>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Suspense>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppShell />
        <WhatsAppFloatingButton />
      </AuthProvider>
    </ErrorBoundary>
  );
}
