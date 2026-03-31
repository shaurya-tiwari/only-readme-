import { useEffect, useState } from "react";
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
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");

  const redirectTarget = location.state?.from?.pathname;

  useEffect(() => {
    document.title = "Sign In | RideShield";
  }, []);

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
          description="Worker and admin sessions are separate so protection flows and operations controls stay clean."
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
              <input className="field" value={adminUsername} onChange={(e) => setAdminUsername(e.target.value)} placeholder="Enter admin username" required />
            </div>
            <div>
              <label className="label">Admin password</label>
              <input className="field" type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} placeholder="Enter admin password" required />
            </div>
            <button type="submit" className="button-primary w-full" disabled={loading}>
              {loading ? "Signing in..." : "Continue as admin"}
            </button>
            <p className="text-sm text-ink/60">
              Local demo access uses the configured admin credentials from the project environment.
            </p>
          </form>
        )}
      </div>

      <div className="panel p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-on-surface-variant">Why RideShield</p>
        <h2 className="mt-2 text-3xl font-bold text-primary">Income protection that feels automatic, not bureaucratic.</h2>
        <div className="mt-6 space-y-4 text-sm text-ink/65">
          <p>Workers do not file claims manually. RideShield monitors zone-level disruptions, matches active policies, and pays automatically when confidence is high.</p>
          <p>Admins see the pressure points behind the engine: delayed reviews, duplicate prevention, payout movement, and scheduler status.</p>
          <p>The product is built to explain outcomes clearly so approved, delayed, and rejected claims never feel arbitrary.</p>
        </div>
      </div>
    </div>
  );
}
