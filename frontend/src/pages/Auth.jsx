import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import SectionHeader from "../components/SectionHeader";

export default function Auth() {
  const navigate = useNavigate();
  const location = useLocation();
  const { loginWorker, loginAdmin } = useAuth();
  const [tab, setTab] = useState("worker");
  const [loading, setLoading] = useState(false);
  const [workerPhone, setWorkerPhone] = useState("");
  const [adminUsername, setAdminUsername] = useState("admin");
  const [adminPassword, setAdminPassword] = useState("rideshield-admin");

  const redirectTarget = location.state?.from?.pathname;

  async function handleWorkerLogin(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await loginWorker(workerPhone);
      navigate(redirectTarget || `/dashboard/${result.session.worker_id}`, { replace: true });
    } finally {
      setLoading(false);
    }
  }

  async function handleAdminLogin(event) {
    event.preventDefault();
    setLoading(true);
    try {
      await loginAdmin(adminUsername, adminPassword);
      navigate(redirectTarget || "/admin", { replace: true });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[0.95fr_1.05fr]">
      <div className="panel p-8">
        <SectionHeader
          eyebrow="Access"
          title="Sign in to RideShield"
          description="Worker sign-in and admin sign-in now run as separate Sprint 3 flows."
        />

        <div className="mb-6 flex gap-2 rounded-2xl bg-black/[0.04] p-1">
          <button type="button" className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold ${tab === "worker" ? "bg-white shadow" : ""}`} onClick={() => setTab("worker")}>
            Worker sign in
          </button>
          <button type="button" className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold ${tab === "admin" ? "bg-white shadow" : ""}`} onClick={() => setTab("admin")}>
            Admin sign in
          </button>
        </div>

        {tab === "worker" ? (
          <form className="space-y-5" onSubmit={handleWorkerLogin}>
            <div>
              <label className="label">Registered phone number</label>
              <input className="field" value={workerPhone} onChange={(e) => setWorkerPhone(e.target.value)} placeholder="+919876543210" required />
            </div>
            <button type="submit" className="button-primary w-full" disabled={loading}>
              {loading ? "Signing in..." : "Continue as worker"}
            </button>
            <p className="text-sm text-ink/60">
              New here? <Link to="/onboarding" className="font-semibold text-storm">Create a worker profile</Link>
            </p>
          </form>
        ) : (
          <form className="space-y-5" onSubmit={handleAdminLogin}>
            <div>
              <label className="label">Admin username</label>
              <input className="field" value={adminUsername} onChange={(e) => setAdminUsername(e.target.value)} required />
            </div>
            <div>
              <label className="label">Admin password</label>
              <input className="field" type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} required />
            </div>
            <button type="submit" className="button-primary w-full" disabled={loading}>
              {loading ? "Signing in..." : "Continue as admin"}
            </button>
          </form>
        )}
      </div>

      <div className="panel p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Sprint 3 fixes</p>
        <h2 className="mt-2 text-3xl font-bold">What changes here</h2>
        <div className="mt-6 space-y-4 text-sm text-ink/65">
          <p>Worker registration and worker sign-in are no longer the same thing.</p>
          <p>Admin access now has a separate session role and route boundary.</p>
          <p>Session restore runs against the backend instead of relying only on a route parameter.</p>
        </div>
      </div>
    </div>
  );
}
