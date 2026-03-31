import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppFrame from "./components/AppFrame";
import ErrorBoundary from "./components/ErrorBoundary";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

const Auth = lazy(() => import("./pages/Auth"));
const Home = lazy(() => import("./pages/Home"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const IntelligenceOverview = lazy(() => import("./pages/IntelligenceOverview"));
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
    <div className="min-h-screen text-ink">
      <Suspense fallback={<div className="panel m-6 p-8 text-center text-ink/60">Loading page...</div>}>
        <Routes>
          <Route
            path="/"
            element={(
              <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
                <Navbar session={session?.session} />
                <Home />
              </div>
            )}
          />
          <Route
            path="/how-it-works"
            element={(
              <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
                <Navbar session={session?.session} />
                <HowItWorks />
              </div>
            )}
          />
          <Route
            path="/auth"
            element={(
              <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
                <Navbar session={session?.session} />
                <RedirectIfAuth>
                  <Auth />
                </RedirectIfAuth>
              </div>
            )}
          />
          <Route
            path="/onboarding"
            element={(
              <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
                <Navbar session={session?.session} />
                <RedirectIfAuth>
                  <Onboarding />
                </RedirectIfAuth>
              </div>
            )}
          />
          <Route
            path="/dashboard"
            element={(
              <ProtectedRoute role="worker">
                <AppFrame>
                  <Dashboard />
                </AppFrame>
              </ProtectedRoute>
            )}
          />
          <Route
            path="/dashboard/:workerId"
            element={(
              <ProtectedRoute role="worker">
                <AppFrame>
                  <Dashboard />
                </AppFrame>
              </ProtectedRoute>
            )}
          />
          <Route
            path="/intelligence"
            element={(
              <ProtectedRoute role="admin">
                <AppFrame>
                  <IntelligenceOverview />
                </AppFrame>
              </ProtectedRoute>
            )}
          />
          <Route
            path="/admin"
            element={(
              <ProtectedRoute role="admin">
                <AppFrame>
                  <AdminPanel />
                </AppFrame>
              </ProtectedRoute>
            )}
          />
          <Route
            path="/demo"
            element={(
              <ProtectedRoute role="admin">
                <AppFrame>
                  <DemoRunner />
                </AppFrame>
              </ProtectedRoute>
            )}
          />
        </Routes>
      </Suspense>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <AppShell />
      </ErrorBoundary>
    </AuthProvider>
  );
}
