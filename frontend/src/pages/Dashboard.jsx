import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { RefreshCcw } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { claimsApi } from "../api/claims";
import { eventsApi } from "../api/events";
import { payoutsApi } from "../api/payouts";
import { policiesApi } from "../api/policies";
import { workersApi } from "../api/workers";
import ActivePolicyCard from "../components/ActivePolicyCard";
import ClaimDetailPanel from "../components/ClaimDetailPanel";
import ClaimList from "../components/ClaimList";
import ClaimStatus from "../components/ClaimStatus";
import EventPanel from "../components/EventPanel";
import PayoutHistory from "../components/PayoutHistory";
import SectionHeader from "../components/SectionHeader";
import StatCard from "../components/StatCard";
import TrustBadge from "../components/TrustBadge";
import { formatCurrency, humanizeSlug } from "../utils/formatters";

export default function Dashboard() {
  const { workerId } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const [loading, setLoading] = useState(true);
  const [worker, setWorker] = useState(null);
  const [policyState, setPolicyState] = useState(null);
  const [claims, setClaims] = useState(null);
  const [payouts, setPayouts] = useState(null);
  const [events, setEvents] = useState([]);
  const [selectedClaim, setSelectedClaim] = useState(null);

  useEffect(() => {
    let active = true;
    const effectiveWorkerId = workerId || session?.session?.worker_id;

    if (!effectiveWorkerId) {
      setLoading(false);
      return () => {
        active = false;
      };
    }

    async function load() {
      setLoading(true);
      try {
        const [workerRes, policyRes, claimsRes, payoutsRes, eventsRes] = await Promise.all([
          workersApi.profile(effectiveWorkerId),
          policiesApi.active(effectiveWorkerId),
          claimsApi.worker(effectiveWorkerId, { days: 30 }),
          payoutsApi.worker(effectiveWorkerId, { days: 30 }),
          eventsApi.active(),
        ]);

        if (!active) {
          return;
        }

        const claimsPayload = claimsRes.data;
        setWorker(workerRes.data);
        setPolicyState(policyRes.data);
        setClaims(claimsPayload);
        setPayouts(payoutsRes.data);
        setEvents(eventsRes.data.events || []);
        setSelectedClaim(claimsPayload.claims?.[0] || null);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [workerId, session]);

  useEffect(() => {
    let active = true;

    async function loadDetail() {
      if (!selectedClaim?.id) {
        return;
      }
      const detail = await claimsApi.detail(selectedClaim.id);
      if (active) {
        setSelectedClaim(detail.data);
      }
    }

    if (selectedClaim?.id && !selectedClaim.decision_breakdown?.breakdown) {
      loadDetail();
    }

    return () => {
      active = false;
    };
  }, [selectedClaim?.id]);

  if (loading) {
    return <div className="panel p-8 text-center text-ink/60">Loading dashboard...</div>;
  }

  if (!worker) {
    return (
      <div className="panel p-8">
        <p className="text-xl font-bold">Worker not found</p>
        <button type="button" className="button-secondary mt-4" onClick={() => navigate("/auth")}>
          Back to sign in
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Worker dashboard"
        title={`${worker.name} · ${humanizeSlug(worker.city)}`}
        description={`${worker.platform} · ${worker.zone ? humanizeSlug(worker.zone) : "No zone"} · live view of coverage, claims, payouts, and nearby disruptions.`}
        action={(
          <button type="button" className="button-secondary" onClick={() => window.location.reload()}>
            <RefreshCcw size={16} />
            Refresh
          </button>
        )}
      />

      <div className="flex flex-wrap items-center gap-3">
        <TrustBadge score={worker.trust_score} />
        <span className="pill bg-black/[0.05] text-ink/65">Risk score {Number(worker.risk_score || 0).toFixed(3)}</span>
        <span className="pill bg-black/[0.05] text-ink/65">Status {humanizeSlug(worker.status)}</span>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Approved claims" value={claims?.approved ?? 0} hint={`${claims?.total ?? 0} total claims`} tone="storm" />
        <StatCard label="Total payouts" value={formatCurrency(payouts?.total_amount)} hint={`${payouts?.total_payouts ?? 0} transfers`} tone="forest" />
        <StatCard label="This week" value={formatCurrency(payouts?.this_week_amount)} hint={`${payouts?.this_week_count ?? 0} payouts`} tone="gold" />
        <StatCard label="Current zone" value={worker.zone ? humanizeSlug(worker.zone) : "--"} hint={worker.city} tone="ember" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <ActivePolicyCard policy={policyState?.active_policy} pendingPolicy={policyState?.pending_policy} />
        <EventPanel events={events.filter((event) => event.zone === worker.zone)} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel p-6">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Claims</p>
            <h3 className="mt-1 text-2xl font-bold">Recent worker incidents</h3>
          </div>
          <ClaimList claims={claims?.claims || []} onSelect={setSelectedClaim} />
        </div>
        <div className="space-y-6">
          <ClaimStatus claim={selectedClaim} />
          <ClaimDetailPanel claim={selectedClaim} />
        </div>
      </div>

      <PayoutHistory data={payouts} />
    </div>
  );
}
