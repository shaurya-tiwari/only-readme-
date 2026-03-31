import { useCallback, useEffect, useMemo, useState } from "react";
import { MapPin, RefreshCcw, ShieldCheck, Wallet } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

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
import TrustBadge from "../components/TrustBadge";
import TrustScoreGauge from "../components/TrustScoreGauge";
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

  const effectiveWorkerId = workerId || session?.session?.worker_id;

  const load = useCallback(async () => {
    if (!effectiveWorkerId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const [workerRes, policyRes, claimsRes, payoutsRes, eventsRes] = await Promise.all([
        workersApi.profile(effectiveWorkerId),
        policiesApi.active(effectiveWorkerId),
        claimsApi.worker(effectiveWorkerId, { days: 30 }),
        payoutsApi.worker(effectiveWorkerId, { days: 30 }),
        eventsApi.active(),
      ]);

      const claimsPayload = claimsRes.data;
      setWorker(workerRes.data);
      setPolicyState(policyRes.data);
      setClaims(claimsPayload);
      setPayouts(payoutsRes.data);
      setEvents(eventsRes.data.events || []);
      setSelectedClaim((current) => current || claimsPayload.claims?.[0] || null);
    } finally {
      setLoading(false);
    }
  }, [effectiveWorkerId]);

  useEffect(() => {
    document.title = "Worker Dashboard | RideShield";
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
  }, [selectedClaim?.id, selectedClaim?.decision_breakdown]);

  const latestPayout = payouts?.payouts?.[0];
  const approvedClaims = claims?.approved ?? 0;
  const totalClaims = claims?.total ?? 0;

  const coverageNarrative = useMemo(() => {
    if (latestPayout) {
      return `Latest payout ${formatCurrency(latestPayout.amount)} credited automatically after system validation.`;
    }
    if (approvedClaims > 0) {
      return `${approvedClaims} approved claims so far with zero worker filing steps.`;
    }
    return "Coverage is live and waiting for the next verified disruption in the worker zone.";
  }, [latestPayout, approvedClaims]);

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

  const workerEvents = events.filter((event) => event.zone === worker.zone);
  const nearbyAlerts = workerEvents.slice(0, 2);

  return (
    <div className="space-y-8">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-on-surface-variant">
            <MapPin size={16} />
            <span>
              {humanizeSlug(worker.city)} · {worker.zone ? humanizeSlug(worker.zone) : "No zone"}
            </span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-primary">Worker Dashboard</h1>
        </div>
        <button type="button" className="button-secondary !rounded-full !py-2" onClick={load}>
          <RefreshCcw size={16} />
          Refresh
        </button>
      </section>

      <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-6">
          <div className="hero-glow hero-mesh rounded-[32px] p-8">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-white/80">
              <ShieldCheck size={14} />
              Zero-touch claims
            </div>
            <h2 className="mt-6 max-w-2xl text-4xl font-bold leading-tight">{worker.name}, your protection runs in the background.</h2>
            <p className="mt-4 max-w-xl text-base leading-8 text-white/78">
              RideShield watches live disruption signals in your zone, merges overlapping triggers into one incident, checks policy coverage, and decides payout without asking you to file a manual claim.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <div className="rounded-[22px] border-b-4 border-[#85bdbc] bg-white/10 p-5">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Approved claims</p>
                <p className="mt-3 text-3xl font-bold">{approvedClaims}</p>
              </div>
              <div className="rounded-[22px] border-b-4 border-[#f4a135] bg-white/10 p-5">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Total payouts</p>
                <p className="mt-3 text-3xl font-bold">{formatCurrency(payouts?.total_amount)}</p>
              </div>
              <div className="rounded-[22px] border-b-4 border-white/70 bg-white/10 p-5">
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Claim window</p>
                <p className="mt-3 text-3xl font-bold">{totalClaims}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="panel p-6">
              <p className="eyebrow">Latest payout</p>
              <p className="mt-4 text-3xl font-bold text-primary">{latestPayout ? formatCurrency(latestPayout.amount) : "INR 0"}</p>
              <p className="mt-3 text-sm text-on-surface-variant">{latestPayout ? "Credited to wallet and recorded in payout history" : "No wallet transfer yet"}</p>
            </div>
            <div className="panel p-6">
              <p className="eyebrow">Protection status</p>
              <div className="mt-4 flex items-center gap-3">
                <span className={`pill ${policyState?.active_policy ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                  <span className={`mr-2 inline-block h-2 w-2 rounded-full ${policyState?.active_policy ? "bg-emerald-500" : "bg-amber-500"}`} />
                  {policyState?.active_policy ? "Active & shielded" : "Pending activation"}
                </span>
              </div>
              <p className="mt-3 text-sm text-on-surface-variant">Coverage and waiting-period aware</p>
            </div>
            <div className="panel p-6 md:col-span-2">
              <p className="eyebrow">Trust score</p>
              <div className="mt-4">
                <TrustScoreGauge score={worker.trust_score} />
              </div>
            </div>
          </div>

          <div className="panel p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="eyebrow">Claims history</p>
                <h3 className="mt-2 text-2xl font-bold text-primary">Incident-aligned claim history</h3>
              </div>
            </div>
            <ClaimList claims={claims?.claims || []} onSelect={setSelectedClaim} />
          </div>
        </section>

        <aside className="space-y-6">
          <ActivePolicyCard policy={policyState?.active_policy} pendingPolicy={policyState?.pending_policy} />

          <div className="panel p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="eyebrow">Nearby alerts</p>
                <h3 className="mt-2 text-2xl font-bold text-primary">Zone pressure</h3>
              </div>
              <TrustBadge score={worker.trust_score} />
            </div>
            {nearbyAlerts.length ? (
              <div className="space-y-3">
                {nearbyAlerts.map((event) => (
                  <div key={event.id} className="rounded-[22px] border-l-4 border-primary bg-surface-container-low p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">
                        {(event.metadata_json?.fired_triggers || [event.event_type]).map(humanizeSlug).join(", ")}
                      </p>
                      <span className="text-xs font-semibold text-primary">{Math.round(Number(event.disruption_score || 0) * 100)}%</span>
                    </div>
                    <div className="mt-3 h-2 rounded-full bg-surface-container">
                      <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.max(12, Math.round(Number(event.disruption_score || 0) * 100))}%` }} />
                    </div>
                    <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                      {humanizeSlug(event.zone)} · disruption score {Number(event.disruption_score || 0).toFixed(3)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-on-surface-variant">No nearby active disruptions right now.</p>
            )}
          </div>

          <ClaimStatus claim={selectedClaim} />

          <div className="panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <Wallet size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">Protection narrative</h3>
            </div>
            <p className="text-sm leading-7 text-on-surface-variant">{coverageNarrative}</p>
          </div>
        </aside>
      </div>

      <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-6">
          <ClaimDetailPanel claim={selectedClaim} />
          <PayoutHistory data={payouts} />
        </section>

        <EventPanel events={workerEvents} />
      </div>
    </div>
  );
}
