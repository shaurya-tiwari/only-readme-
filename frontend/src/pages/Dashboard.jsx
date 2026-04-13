import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ChevronDown, ChevronUp, MapPin, RefreshCcw, Shield, ShieldCheck, ShieldOff, Wallet } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";

import { useAuth } from "../auth/AuthContext";
import { claimsApi } from "../api/claims";
import { eventsApi } from "../api/events";
import { payoutsApi } from "../api/payouts";
import { policiesApi } from "../api/policies";
import { workersApi } from "../api/workers";
import ActivePolicyCard from "../components/ActivePolicyCard";
import ClaimDetailPanel from "../components/ClaimDetailPanel";
import ClaimList from "../components/ClaimList";
import DecisionPanel from "../components/DecisionPanel";
import ErrorState from "../components/ErrorState";
import EventPanel from "../components/EventPanel";
import PayoutHistory from "../components/PayoutHistory";
import RiskScoreCard from "../components/RiskScoreCard";
import TrustBadge from "../components/TrustBadge";
import TrustScoreGauge from "../components/TrustScoreGauge";
import { formatCurrency, formatDateTime, humanizeSlug } from "../utils/formatters";
import { getDisruptionTone } from "../utils/toneHelpers";

function claimPriority(claim) {
  if (!claim) return -1;
  if (claim.status === "delayed") return 3;
  if (claim.status === "rejected") return 2;
  if (claim.status === "approved") return 1;
  return 0;
}

/* ─── Policy Gate: First-time user ─── */
function FirstTimeGate({ workerId, onPurchased }) {
  const [plans, setPlans] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);

  useEffect(() => {
    policiesApi.plans(workerId).then((res) => {
      setPlans(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [workerId]);

  async function handlePurchase(planName) {
    setPurchasing(planName);
    try {
      await policiesApi.create({ worker_id: workerId, plan_name: planName });
      toast.success("Policy purchased! It will activate after the waiting period.");
      onPurchased();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Purchase failed.");
    } finally {
      setPurchasing(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-12">
      <div className="text-center">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
          <Shield size={40} className="text-primary" />
        </div>
        <h1 className="mt-6 text-4xl font-bold tracking-tight text-primary">Get Protected</h1>
        <p className="mt-4 text-lg leading-8 text-on-surface-variant">
          Choose a plan to activate your income protection. RideShield watches for disruptions in
          your zone and automatically processes claims — zero paperwork.
        </p>
      </div>

      {loading ? (
        <div className="text-center text-on-surface-variant">Loading plans...</div>
      ) : plans?.plans ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plans.plans.map((plan) => (
            <div
              key={plan.plan_name}
              className={`panel p-6 transition-smooth hover:shadow-lg ${
                plan.plan_name === plans.recommended ? "ring-2 ring-primary" : ""
              }`}
            >
              {plan.plan_name === plans.recommended && (
                <span className="pill badge-active mb-3 inline-block text-xs">Recommended</span>
              )}
              <h3 className="text-xl font-bold text-primary">{plan.display_name}</h3>
              <p className="mt-2 text-3xl font-extrabold text-on-surface">
                {formatCurrency(plan.weekly_premium)}
                <span className="text-sm font-normal text-on-surface-variant">/week</span>
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">
                Up to {formatCurrency(plan.coverage_cap)} coverage
              </p>
              <div className="mt-3 flex flex-wrap gap-1">
                {(plan.triggers_covered || []).map((t) => (
                  <span key={t} className="pill text-xs">{humanizeSlug(t)}</span>
                ))}
              </div>
              <button
                type="button"
                className="button-primary mt-5 w-full"
                disabled={!!purchasing}
                onClick={() => handlePurchase(plan.plan_name)}
              >
                {purchasing === plan.plan_name ? "Purchasing..." : "Buy Plan"}
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-on-surface-variant">Unable to load plans.</div>
      )}
    </div>
  );
}

/* ─── Policy Gate: Expired user ─── */
function ExpiredGate({ workerId, lastPolicy, onPurchased }) {
  const [purchasing, setPurchasing] = useState(false);

  async function handleRenew() {
    setPurchasing(true);
    try {
      await policiesApi.create({ worker_id: workerId, plan_name: lastPolicy.plan_name });
      toast.success("Coverage renewed! It will activate after the waiting period.");
      onPurchased();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Renewal failed.");
    } finally {
      setPurchasing(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-8 py-12">
      <div className="text-center">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-amber-500/10">
          <ShieldOff size={40} className="text-amber-500" />
        </div>
        <h1 className="mt-6 text-4xl font-bold tracking-tight text-amber-400">
          Your coverage expired
        </h1>
        <p className="mt-4 text-lg leading-8 text-on-surface-variant">
          Your protection is no longer active. Renew to keep your income shielded from disruptions.
        </p>
      </div>

      <div className="panel p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Last plan</p>
            <h3 className="mt-2 text-2xl font-bold text-primary">
              {lastPolicy.display_name || humanizeSlug(lastPolicy.plan_name)}
            </h3>
          </div>
          <span className="pill badge-warning">Expired</span>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="panel-quiet rounded-[24px] p-4">
            <p className="text-sm text-on-surface-variant">Premium was</p>
            <p className="mt-2 text-xl font-bold text-primary">
              {formatCurrency(lastPolicy.weekly_premium)}/week
            </p>
          </div>
          <div className="panel-quiet rounded-[24px] p-4">
            <p className="text-sm text-on-surface-variant">Coverage cap</p>
            <p className="mt-2 text-xl font-bold text-primary">
              {formatCurrency(lastPolicy.coverage_cap)}
            </p>
          </div>
          <div className="panel-quiet rounded-[24px] p-4">
            <p className="text-sm text-on-surface-variant">Expired on</p>
            <p className="mt-2 text-sm font-semibold text-primary">
              {formatDateTime(lastPolicy.expired_at)}
            </p>
          </div>
        </div>
        <button
          type="button"
          className="button-primary mt-6 w-full"
          disabled={purchasing}
          onClick={handleRenew}
        >
          {purchasing ? "Renewing..." : "Renew Coverage"}
        </button>
      </div>

      <p className="text-center text-sm text-on-surface-variant">
        Want a different plan?{" "}
        <button
          type="button"
          className="font-semibold text-primary underline"
          onClick={() => window.location.reload()}
        >
          View all plans
        </button>
      </p>
    </div>
  );
}

/* ─── Main Dashboard ─── */
export default function Dashboard() {
  const { workerId } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [worker, setWorker] = useState(null);
  const [policyState, setPolicyState] = useState(null);
  const [claims, setClaims] = useState(null);
  const [payouts, setPayouts] = useState(null);
  const [events, setEvents] = useState([]);
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [claimDetailOpen, setClaimDetailOpen] = useState(false);

  const effectiveWorkerId = workerId || session?.session?.worker_id;

  const load = useCallback(async () => {
    if (!effectiveWorkerId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
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
      setSelectedClaim((current) => {
        if (current) return current;
        const claimsList = [...(claimsPayload.claims || [])];
        claimsList.sort((a, b) => {
          const statusDelta = claimPriority(b) - claimPriority(a);
          if (statusDelta !== 0) return statusDelta;
          return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
        });
        return claimsList[0] || null;
      });
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load dashboard data.");
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
        setClaimDetailOpen(true);
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
  const activeDecisionClaim = selectedClaim || claims?.claims?.[0] || null;
  const urgentClaim =
    (claims?.claims || []).find((claim) => claim.status === "delayed") ||
    (claims?.claims || []).find((claim) => claim.status === "rejected") ||
    activeDecisionClaim;

  const coverageNarrative = useMemo(() => {
    if (latestPayout) {
      return `Latest payout ${formatCurrency(latestPayout.amount)} credited automatically after system validation.`;
    }
    if (approvedClaims > 0) {
      return `${approvedClaims} approved claims so far with zero worker filing steps.`;
    }
    return "Coverage is live and waiting for the next verified disruption in the worker zone.";
  }, [latestPayout, approvedClaims]);
  const latestPayoutState =
    latestPayout?.status === "failed"
      ? "Transfer failed, claim still protected"
      : latestPayout?.status === "processing"
        ? "Transfer in progress"
        : latestPayout?.status === "pending"
          ? "Transfer queued"
          : latestPayout
            ? "Credited to wallet and recorded in payout history"
            : "No wallet transfer yet";

  if (loading) {
    return <div className="panel p-8 text-center text-on-surface-variant">Loading dashboard...</div>;
  }

  if (error) {
    return <ErrorState message={error} onRetry={load} />;
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

  /* ─── Policy Gate ─── */
  const hasPolicy = policyState?.active_policy || policyState?.pending_policy;

  if (!hasPolicy) {
    const lastExpired = policyState?.last_expired_policy;

    if (lastExpired) {
      return (
        <ExpiredGate
          workerId={effectiveWorkerId}
          lastPolicy={lastExpired}
          onPurchased={() => load()}
        />
      );
    }

    return <FirstTimeGate workerId={effectiveWorkerId} onPurchased={() => load()} />;
  }

  const workerEvents = events.filter((event) => event.zone === worker.zone);
  const nearbyAlerts = workerEvents.slice(0, 2);

  return (
    <div className="space-y-6">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-on-surface-variant">
            <MapPin size={16} />
            <span>
              {humanizeSlug(worker.city)} - {worker.zone ? humanizeSlug(worker.zone) : "No zone"}
            </span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-primary">Worker Dashboard</h1>
        </div>
        <button type="button" className="button-secondary !rounded-full !py-2" onClick={load}>
          <RefreshCcw size={16} />
          Refresh
        </button>
      </section>

      {/* Hero card — full width */}
      <div className="hero-glow hero-mesh rounded-[32px] p-8 scale-pop">
        <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-white/80 backdrop-blur-sm">
          <ShieldCheck size={14} />
          Zero-touch claims
        </div>
        <h2 className="mt-6 max-w-2xl text-5xl font-bold leading-tight">
          {worker.name}, your protection runs in the background.
        </h2>
        <p className="mt-4 max-w-xl text-base leading-8 text-white/78">
          RideShield watches disruption signals in your zone, merges overlapping triggers into one incident, checks
          policy coverage, and decides payout without asking you to file a manual claim.
        </p>

        <div className="mt-8 grid gap-4 grid-cols-12">
          <div className="col-span-12 sm:col-span-7 rounded-[22px] border-b-4 border-emerald-600 bg-white/10 p-6 transition-smooth hover:bg-white/15 backdrop-blur-sm">
            <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Approved claims</p>
            <p className="mt-4 text-5xl font-extrabold">{approvedClaims}</p>
            <p className="mt-2 text-xs text-white/60">Of {totalClaims} total claims filed</p>
          </div>
          <div className="col-span-12 sm:col-span-5 rounded-[22px] border-b-4 border-amber-500 bg-white/10 p-6 transition-smooth hover:bg-white/15 backdrop-blur-sm">
            <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Total payouts</p>
            <p className="mt-4 text-4xl font-extrabold">{formatCurrency(payouts?.total_amount)}</p>
          </div>
          <div className="col-span-12 rounded-[22px] border-b-4 border-blue-400 bg-white/10 p-6 transition-smooth hover:bg-white/15 backdrop-blur-sm">
            <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Coverage window</p>
            <p className="mt-4 text-2xl font-extrabold">{totalClaims} claims tracked</p>
            <p className="mt-2 text-xs text-white/60">Latest 30 days</p>
          </div>
        </div>
      </div>

      {/* Decision Panel — full width */}
      <DecisionPanel claim={urgentClaim} narrative={coverageNarrative} />

      {/* Claim Detail — collapsible full width */}
      {urgentClaim && (
        <div className="context-panel overflow-hidden rounded-[28px]">
          <button
            type="button"
            className="flex w-full items-center justify-between px-6 py-4 text-left transition-smooth hover:bg-surface-container"
            onClick={() => setClaimDetailOpen(!claimDetailOpen)}
          >
            <div className="flex items-center gap-3">
              <p className="eyebrow !mb-0">Claim detail</p>
              <span className="text-sm text-on-surface-variant">
                {humanizeSlug(urgentClaim.trigger_type || "incident")} — {humanizeSlug(urgentClaim.status)}
              </span>
            </div>
            {claimDetailOpen ? <ChevronUp size={18} className="text-on-surface-variant" /> : <ChevronDown size={18} className="text-on-surface-variant" />}
          </button>
          {claimDetailOpen && (
            <div className="border-t border-outline-variant/20 px-0">
              <ClaimDetailPanel claim={urgentClaim} />
            </div>
          )}
        </div>
      )}

      {/* Active Policy — full width */}
      <ActivePolicyCard policy={policyState?.active_policy} pendingPolicy={policyState?.pending_policy} />

      {/* Active Incidents + Coverage Outlook — side by side */}
      <div className="grid items-start gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <EventPanel events={workerEvents} />
        <RiskScoreCard workerId={effectiveWorkerId} />
      </div>

      {/* Claims History + Payout History — side by side */}
      <div className="grid items-start gap-6 xl:grid-cols-2">
        <div className="context-panel card-secondary p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="eyebrow">Claims history</p>
              <h3 className="mt-2 text-2xl font-bold text-primary">Incident-aligned claim history</h3>
            </div>
            {urgentClaim?.id ? (
              <button
                type="button"
                className="button-secondary !rounded-full !py-2"
                onClick={() => {
                  setSelectedClaim(urgentClaim);
                  setClaimDetailOpen(true);
                }}
              >
                <ArrowDownRight size={16} />
                Focus current claim
              </button>
            ) : null}
          </div>
          <ClaimList claims={claims?.claims || []} onSelect={(claim) => { setSelectedClaim(claim); setClaimDetailOpen(true); }} />
        </div>

        <PayoutHistory data={payouts} />
      </div>

      {/* Payout + Protection status + Trust */}
      <div className="grid gap-6 grid-cols-12">
        <div className="col-span-12 md:col-span-7 context-panel p-6 border-accent-left border-accent-success">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="eyebrow">Latest payout</p>
              <p className="mt-4 text-5xl font-bold text-primary">
                {latestPayout ? formatCurrency(latestPayout.amount) : "INR 0"}
              </p>
            </div>
            <div className="mt-1 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100/50">
              <Wallet size={20} className="text-emerald-700" />
            </div>
          </div>
          <p className="mt-4 text-sm text-on-surface-variant">{latestPayoutState}</p>
        </div>
        <div className="col-span-12 md:col-span-5 context-panel p-6 border-accent-left border-accent-warning">
          <p className="eyebrow">Protection status</p>
          <div className="mt-4 flex items-center gap-3">
            <span
              className={`pill ${
                policyState?.active_policy ? "badge-active" : "badge-pending"
              }`}
            >
              <span
                className={`mr-2 inline-block h-2 w-2 rounded-full ${
                  policyState?.active_policy ? "bg-emerald-500" : "bg-amber-500"
                }`}
              />
              {policyState?.active_policy ? "Active and shielded" : "Pending activation"}
            </span>
          </div>
          <p className="mt-3 text-sm text-on-surface-variant">Coverage and waiting-period aware</p>
        </div>
        <div className="col-span-12 context-panel p-6 pulse-glow">
          <p className="eyebrow">Trust score</p>
          <div className="mt-4">
            <TrustScoreGauge score={worker.trust_score} />
          </div>
        </div>
      </div>

      {/* Zone Pressure — compact, secondary */}
      {nearbyAlerts.length > 0 && (
        <div className="context-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <p className="eyebrow !mb-0">Nearby alerts</p>
              <TrustBadge score={worker.trust_score} />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {nearbyAlerts.map((event) => {
              const disruptionLevel = Number(event.disruption_score || 0);
              const tone = getDisruptionTone(disruptionLevel);
              return (
                <div
                  key={event.id}
                  className={`rounded-[16px] border-l-2 p-3 text-sm opacity-90 transition-smooth hover:shadow-md ${tone.border}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-on-surface">
                      {(event.metadata_json?.fired_triggers || [event.event_type]).map(humanizeSlug).join(", ")}
                    </p>
                    <span className="text-xs font-bold text-on-surface">
                      {Math.round(disruptionLevel * 100)}%
                    </span>
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-container-high">
                    <div
                      className={`h-full rounded-full transition-all ${tone.progress}`}
                      style={{ width: `${Math.max(12, Math.round(disruptionLevel * 100))}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs leading-5 text-on-surface-variant">
                    {humanizeSlug(event.zone)} - signal strength {disruptionLevel.toFixed(2)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
