import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, ShieldAlert } from "lucide-react";

import { analyticsApi } from "../api/analytics";
import { claimsApi } from "../api/claims";
import { eventsApi } from "../api/events";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import DisruptionMap from "../components/DisruptionMap";
import ErrorState from "../components/ErrorState";
import EventPanel from "../components/EventPanel";
import ForecastCards from "../components/ForecastCards";
import KpiTile from "../components/KpiTile";
import ModelHealthBadge from "../components/ModelHealthBadge";
import NextDecisionPanel from "../components/NextDecisionPanel";
import ReviewQueue from "../components/ReviewQueue";
import { groupClaimsByIncident } from "../utils/claimGroups";
import { formatAudienceFactor, formatPolicyRule, formatPolicySurface } from "../utils/decisionNarrative";
import { formatCurrency, formatDateTime, formatPercent, formatRelative, humanizeSlug } from "../utils/formatters";

function forecastTone(band) {
  switch (band) {
    case "critical":
      return {
        container: "border-red-400/30",
        pill: "badge-error",
        progress: "bg-red-500",
      };
    case "elevated":
      return {
        container: "border-amber-300/25",
        pill: "badge-pending",
        progress: "bg-amber-500",
      };
    case "guarded":
      return {
        container: "border-blue-300/25",
        pill: "badge-guarded",
        progress: "bg-blue-500",
      };
    default:
      return {
        container: "border-emerald-300/20",
        pill: "badge-active",
        progress: "bg-emerald-500",
      };
  }
}

function queuePressureState(totalPending, overdueCount, exposure) {
  if (!totalPending) {
    return {
      label: "Calm",
      tone: "badge-active",
      summary: "No delayed incidents are blocking the operator right now.",
    };
  }
  if (overdueCount > 0 || exposure >= 400 || totalPending >= 6) {
    return {
      label: "Critical load",
      tone: "badge-error",
      summary: "Oldest and highest-exposure incidents should be cleared before passive monitoring.",
    };
  }
  if (exposure >= 180 || totalPending >= 3) {
    return {
      label: "Managed review",
      tone: "badge-pending",
      summary: "Backlog exists, but the review queue is still inside an expected operating band.",
    };
  }
  return {
    label: "Controlled",
    tone: "badge-guarded",
    summary: "Only a small number of delayed incidents need intervention.",
  };
}

function compactBar(share, tone = "bg-primary") {
  return (
    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-container-high">
      <div
        className={`h-full rounded-full transition-all ${tone}`}
        style={{ width: `${Math.max(4, Math.min(100, Number(share || 0)))}%` }}
      />
    </div>
  );
}

function sourceLabel(signalType, status) {
  const signal = humanizeSlug(signalType);
  if (!status) {
    return `${signal} unavailable`;
  }
  if (status.is_fallback) {
    return `Fallback ${signal.toLowerCase()}`;
  }
  if (status.configured_source === "real" || String(status.latest_provider || "").startsWith("openweather")) {
    return `Live ${signal.toLowerCase()}`;
  }
  return `Mock ${signal.toLowerCase()}`;
}

function sourceTone(status) {
  if (!status) {
    return "badge-pending";
  }
  if (status.is_fallback) {
    return "badge-pending";
  }
  if (status.configured_source === "real" || String(status.latest_provider || "").startsWith("openweather")) {
    return "badge-active";
  }
  return "badge-guarded";
}

export default function AdminPanel() {
  const [selectedCity, setSelectedCity] = useState("all");
  const [selectedZone, setSelectedZone] = useState("all");
  const [cityOptions, setCityOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [claimStats, setClaimStats] = useState(null);
  const [payoutStats, setPayoutStats] = useState(null);
  const [queue, setQueue] = useState(null);
  const [events, setEvents] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [config, setConfig] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);

  useEffect(() => {
    document.title = "Admin Panel | RideShield";
  }, []);

  useEffect(() => {
    load();
    loadCities();
  }, []);

  async function loadCities() {
    try {
      const response = await locationsApi.cities();
      setCityOptions(response.data || []);
    } catch {
      setCityOptions([]);
    }
  }

  async function load() {
    setLoading(true);
    setLoadError(null);
    try {
      const [claimsRes, payoutsRes, queueRes, eventsRes, historyRes, analyticsRes, configRes] = await Promise.all([
        claimsApi.stats({ days: 14 }),
        payoutsApi.stats({ days: 14 }),
        claimsApi.queue(),
        eventsApi.active(),
        eventsApi.history({ days: 14, limit: 20 }),
        analyticsApi.adminOverview({ days: 14 }),
        healthApi.getConfig(),
      ]);
      setClaimStats(claimsRes.data);
      setPayoutStats(payoutsRes.data);
      setQueue(queueRes.data);
      setEvents([...(eventsRes.data.events || []), ...(historyRes.data.events || []).slice(0, 6)]);
      setAnalytics(analyticsRes.data);
      setConfig(configRes.data);
    } catch (err) {
      setLoadError(err?.response?.data?.detail || "Failed to load admin panel data.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(claimId, decision) {
    setResolvingId(claimId);
    try {
      await claimsApi.resolve(claimId, {
        decision,
        reviewed_by: "admin_panel",
        reason: decision === "reject" ? "Rejected from admin panel." : "Approved from admin panel.",
      });
      await load();
    } finally {
      setResolvingId(null);
    }
  }

  const cityFilteredEvents = selectedCity === "all" ? events : events.filter((event) => event.city === selectedCity);
  const zoneOptions = useMemo(
    () => [...new Set(cityFilteredEvents.map((event) => event.zone).filter(Boolean))],
    [cityFilteredEvents],
  );
  const visibleEvents =
    selectedZone === "all" ? cityFilteredEvents : cityFilteredEvents.filter((event) => event.zone === selectedZone);
  const queueClaims = queue?.claims || [];
  const filteredQueueClaims = queueClaims.filter((claim) => {
    const cityMatch = selectedCity === "all" || claim.city === selectedCity;
    const zoneMatch = selectedZone === "all" || claim.zone === selectedZone;
    return cityMatch && zoneMatch;
  });
  const filteredQueueIncidents = useMemo(
    () => groupClaimsByIncident(filteredQueueClaims, { bucketMinutes: 90 }),
    [filteredQueueClaims],
  );
  const topIncident = filteredQueueIncidents[0] || null;
  const integrityPreview = (analytics?.duplicate_claim_log || [])
    .filter((entry) => selectedZone === "all" || entry.details?.zone === selectedZone)
    .slice(0, 4);
  const forecastEntries = (analytics?.next_week_forecast || []).filter(
    (entry) => selectedCity === "all" || entry.city === selectedCity,
  );
  const scheduler = analytics?.scheduler;
  const healthValue = scheduler?.enabled
    ? scheduler?.last_error
      ? "Degraded"
      : "Operational"
    : "Disabled";
  const healthHint = scheduler?.last_error
    ? "Scheduler error detected"
    : scheduler?.enabled
      ? "Scheduler heartbeat healthy"
      : "Scheduler paused";
  const queueExposure = filteredQueueIncidents.reduce(
    (total, incident) => total + Number(incident.payout_risk || incident.total_calculated_payout || 0),
    0,
  );
  const queueOverdueCount = filteredQueueIncidents.reduce(
    (total, incident) => total + Number(incident.overdue_count || 0),
    0,
  );
  const queuePressure = queuePressureState(filteredQueueIncidents.length, queueOverdueCount, queueExposure);
  const fallbackSystemDrivers = useMemo(() => {
    const counts = new Map();
    for (const incident of filteredQueueIncidents) {
      const seen = new Set();
      if (incident.primary_factor) {
        seen.add(incident.primary_factor);
      }
      for (const factor of incident.top_factors || []) {
        if (factor?.label) {
          seen.add(factor.label);
        }
      }
      for (const label of seen) {
        counts.set(label, (counts.get(label) || 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([label, count]) => ({
        label,
        count,
        share: filteredQueueIncidents.length ? Math.round((count / filteredQueueIncidents.length) * 100) : 0,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 3);
  }, [filteredQueueIncidents]);
  const topSystemDrivers = analytics?.review_driver_summary?.drivers?.length
    ? analytics.review_driver_summary.drivers
    : fallbackSystemDrivers;
  const reviewDriverWindowHours = analytics?.review_driver_summary?.window_hours || 1;
  const reviewDriverSource = analytics?.review_driver_summary?.source || "active_queue";
  const reviewInsights = analytics?.review_driver_summary?.insights || {};
  const falseReviewSummary = analytics?.false_review_pattern_summary;
  const replaySummary = analytics?.policy_replay_summary;
  const topFalseReviewPatterns = falseReviewSummary?.dominant_patterns || [];
  const replayLift = replaySummary?.delayed_to_approved_count || 0;
  const replayDrag = replaySummary?.approved_to_delayed_count || 0;
  const topFalseReviewPattern = topFalseReviewPatterns[0];
  const policyHealth = analytics?.policy_health_summary;
  const trafficSourceCounts = analytics?.decision_memory_summary?.traffic_source_counts || {};
  const signalSourceStatus = config?.signal_source_status || {};

  if (loading) {
    return <div className="panel p-8 text-center text-on-surface-variant">Loading admin panel...</div>;
  }

  if (loadError) {
    return <ErrorState message={loadError} onRetry={load} />;
  }

  return (
    <div className="space-y-8">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <p className="eyebrow">Admin controls</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-primary">System Oversight</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-on-surface-variant">
            Operational monitoring for RideShield incidents, review pressure, payout movement, and scheduler heartbeat.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <select
            className="field min-w-44 !rounded-full !bg-surface-container-low !py-2"
            value={selectedCity}
            onChange={(e) => {
              setSelectedCity(e.target.value);
              setSelectedZone("all");
            }}
          >
            <option value="all">All cities</option>
            {cityOptions.map((city) => (
              <option key={city.id} value={city.slug}>
                {city.display_name}
              </option>
            ))}
          </select>
          <select
            className="field min-w-44 !rounded-full !bg-surface-container-low !py-2"
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
          >
            <option value="all">All zones</option>
            {zoneOptions.map((zone) => (
              <option key={zone} value={zone}>
                {humanizeSlug(zone)}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Critical actions</p>
            <h2 className="mt-2 text-3xl font-bold text-primary">Act now</h2>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-on-surface-variant">
              Manual review incidents and the next recommended resolution sit above everything else so the operator can
              clear blockers before scanning passive telemetry.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={`pill ${queuePressure.tone}`}>{queuePressure.label}</span>
            {queue?.high_load_mode ? <span className="pill badge-pending">High load mode active</span> : null}
            <span className="pill-subtle">{filteredQueueIncidents.length} incidents</span>
            <span className="pill-subtle">{queueOverdueCount} overdue</span>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.18fr_0.82fr]">
          <ReviewQueue
            claims={filteredQueueClaims}
            resolvingId={resolvingId}
            onResolve={handleResolve}
            highLoadMode={Boolean(queue?.high_load_mode)}
            highLoadThreshold={queue?.high_load_threshold}
          />

          <div className="space-y-6">
            <NextDecisionPanel incident={topIncident} />

            <div className="panel-muted p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <p className="eyebrow">Queue pressure</p>
                  <h3 className="mt-2 text-xl font-bold text-primary">Backlog posture</h3>
                </div>
                <span className={`pill ${queuePressure.tone}`}>{queuePressure.label}</span>
              </div>
              <p className="text-sm leading-7 text-on-surface-variant">{queuePressure.summary}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                  <p className="text-sm text-on-surface-variant">Pending</p>
                  <p className="mt-2 text-2xl font-bold text-primary">{filteredQueueIncidents.length}</p>
                </div>
                <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                  <p className="text-sm text-on-surface-variant">Overdue</p>
                  <p className="mt-2 text-2xl font-bold text-primary">{queueOverdueCount}</p>
                </div>
                <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                  <p className="text-sm text-on-surface-variant">Exposure</p>
                  <p className="mt-2 text-2xl font-bold text-primary">{formatCurrency(queueExposure)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div>
          <p className="eyebrow">System health</p>
          <h2 className="mt-2 text-3xl font-bold text-primary">Know the posture</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-on-surface-variant">
            KPI movement, scheduler heartbeat, and model explainability sit together so platform health reads as one
            operational layer instead of scattered tiles.
          </p>
        </div>

        <div className="bento-grid">
          <div className="bento-1-4">
            <KpiTile label="Claims" value={claimStats?.total_claims ?? 0} hint={`Approval ${formatPercent(claimStats?.approval_rate)}`} />
          </div>
          <div className="bento-1-4">
            <KpiTile
              label="Approval"
              value={formatPercent(claimStats?.approval_rate)}
              hint={`Zero-touch ${formatPercent(claimStats?.zero_touch_rate ?? claimStats?.auto_approval_rate)}`}
            />
          </div>
          <div className="bento-1-4">
            <KpiTile label="Delayed" value={claimStats?.delayed ?? 0} hint={`Review ${formatPercent(claimStats?.review_rate)} | ${queue?.overdue_count ?? 0} overdue`} />
          </div>
          <div className="bento-1-4">
            <KpiTile label="Fraud rate" value={formatPercent(claimStats?.fraud_rate)} hint="Detection window" />
          </div>
          <div className="bento-1-4">
            <KpiTile label="Payout vol." value={formatCurrency(payoutStats?.total_amount)} hint={`${payoutStats?.total_payouts ?? 0} transfers`} />
          </div>
          <div className="bento-1-4">
            <KpiTile label="Health" value={healthValue} hint={healthHint} accent="dark" />
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[0.95fr_0.85fr_1.2fr]">
          <div className="context-panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <Clock3 size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">System Scheduler</h3>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Status</p>
                <p className="mt-2 text-lg font-semibold text-primary">
                  {analytics?.scheduler?.enabled ? "Monitoring" : "Disabled"}
                </p>
              </div>
              <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Last run</p>
                <p className="mt-2 text-lg font-semibold text-primary">
                  {analytics?.scheduler?.last_finished_at ? formatRelative(analytics.scheduler.last_finished_at) : "--"}
                </p>
              </div>
              <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Next run</p>
                <p className="mt-2 text-lg font-semibold text-primary">
                  {analytics?.scheduler?.next_scheduled_at ? formatRelative(analytics.scheduler.next_scheduled_at) : "--"}
                </p>
              </div>
              <div className="rounded-[20px] border border-primary/10 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Interval</p>
                <p className="mt-2 text-lg font-semibold text-primary">{analytics?.scheduler?.interval_seconds || "--"}s</p>
              </div>
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-5">
              <p className="eyebrow">Model status</p>
              <ModelHealthBadge />
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-5">
              <p className="eyebrow">System explainability</p>
              <h3 className="mt-2 text-lg font-bold leading-tight text-primary">
                {reviewDriverSource === "recent_activity"
                  ? `Top review drivers in the last ${reviewDriverWindowHours}h`
                  : "Top drivers across the active review queue"}
              </h3>
              <p className="mt-3 text-xs leading-6 text-on-surface-variant">
                {reviewDriverSource === "recent_activity"
                  ? "Surface the factors repeating across recent delayed incidents so operators can spot whether review pressure is coming from trust, movement, pre-activity, or broader signal drift."
                  : "No new delayed incidents landed in the last hour, so this panel falls back to the current queue instead of going silent."}
              </p>
            </div>
            {(reviewInsights.weak_signal_overlap_share || reviewInsights.low_trust_share) ? (
              <div className="mb-4 rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm font-semibold text-primary">System insight</p>
                <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                  {reviewInsights.weak_signal_overlap_share || 0}% of current review pressure is driven by weak-signal overlap.
                  {` `}
                  {reviewInsights.low_trust_share || 0}% is driven by low trust.
                </p>
              </div>
            ) : null}
            <div className="space-y-3">
              {topSystemDrivers.length ? (
                topSystemDrivers.map((driver) => (
                  <div key={driver.label} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{formatAudienceFactor(driver.label, "admin")}</p>
                      <span className="pill-subtle">{driver.share}% of recent reviews</span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">
                      {driver.count} recent review incidents currently surface {formatAudienceFactor(driver.label, "admin")}.
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">No review drivers are active because the queue is clear.</p>
              )}
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-5">
              <p className="eyebrow">Decision health</p>
              <h3 className="mt-2 text-lg font-bold leading-tight text-primary">Is the system trusting itself enough?</h3>
              <p className="mt-3 text-xs leading-6 text-on-surface-variant">
                Track how many claims still route into manual review versus cleanly auto-approving in the current window.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Zero-touch rate</p>
                <p className="mt-2 text-2xl font-bold text-primary">
                  {formatPercent(analytics?.decision_health?.zero_touch_rate ?? analytics?.decision_health?.auto_approval_rate)}
                </p>
                <p className="mt-2 text-xs text-on-surface-variant">
                  {analytics?.decision_health?.zero_touch_approvals ?? analytics?.decision_health?.auto_approved ?? 0} claims were approved without manual review.
                </p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Review rate</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(analytics?.decision_health?.review_rate)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">
                  {analytics?.decision_health?.claim_total ?? 0} claims were evaluated in the current reporting window.
                </p>
              </div>
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-5">
              <p className="eyebrow">Signal source status</p>
              <h3 className="mt-2 text-lg font-bold leading-tight text-primary">What data is live, mocked, or falling back</h3>
              <p className="mt-3 text-xs leading-6 text-on-surface-variant">
                Real-provider work should be visible to the operator. If a signal falls back, that should read as an explicit runtime state, not hidden infrastructure behavior.
              </p>
            </div>
            <div className="space-y-3">
              {["weather", "aqi", "traffic", "platform"].map((signalType) => {
                const status = signalSourceStatus[signalType];
                return (
                  <div key={signalType} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{sourceLabel(signalType, status)}</p>
                      <span className={`pill ${sourceTone(status)}`}>
                        {status?.is_fallback ? "Fallback" : humanizeSlug(status?.configured_source || "unknown")}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">
                      Provider {humanizeSlug(status?.latest_provider || status?.configured_source || "unknown")}
                      {status?.latency_ms != null ? ` | ${status.latency_ms}ms` : ""}
                    </p>
                    <p className="mt-1 text-xs text-on-surface-variant">
                      {status?.captured_at ? `Last capture ${formatDateTime(status.captured_at)}` : "No captured snapshot yet."}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-5">
              <p className="eyebrow">Calibration watch</p>
              <h3 className="mt-2 text-lg font-bold leading-tight text-primary">What current memory says should change</h3>
              <p className="mt-3 text-xs leading-6 text-on-surface-variant">
                This is the Phase 3 bridge between observed false reviews and safer zero-touch routing.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Replay lift</p>
                <p className="mt-2 text-2xl font-bold text-primary">{replayLift}</p>
                <p className="mt-2 text-xs text-on-surface-variant">
                  Old delayed claims the current policy would now auto-approve.
                </p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Replay drag</p>
                <p className="mt-2 text-2xl font-bold text-primary">{replayDrag}</p>
                <p className="mt-2 text-xs text-on-surface-variant">
                  Previously approved claims the replay would now pull back into review.
                </p>
              </div>
            </div>
            <div className="mt-4 rounded-[18px] border border-primary/8 bg-surface-container-low/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-semibold text-primary">False-review concentration</p>
                <span className="pill-subtle">{falseReviewSummary?.false_review_count || 0} cases</span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {Object.entries(falseReviewSummary?.score_band_distribution || {})
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 2)
                  .map(([band, count]) => {
                    const share = falseReviewSummary?.false_review_count
                      ? Math.round((count / falseReviewSummary.false_review_count) * 100)
                      : 0;
                    return (
                      <div key={band} className="rounded-[16px] border border-primary/6 bg-surface-container-high/70 p-3">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-on-surface-variant">{band.replaceAll("_", ".")}</p>
                        <p className="mt-2 text-lg font-bold text-primary">{count}</p>
                        <p className="text-xs text-on-surface-variant">{share}% of false reviews</p>
                        {compactBar(share)}
                      </div>
                    );
                  })}
              </div>
              {topFalseReviewPatterns[0] ? (
                <p className="mt-4 text-sm leading-6 text-on-surface-variant">
                  Dominant pattern:{" "}
                  <span className="font-semibold text-primary">
                    {topFalseReviewPattern.flags.length
                      ? topFalseReviewPattern.flags.map(humanizeSlug).join(" + ")
                      : "No flags"}
                  </span>{" "}
                  at {topFalseReviewPattern.share}% of observed false reviews.
                </p>
              ) : null}
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-5">
              <p className="eyebrow">Policy health</p>
              <h3 className="mt-2 text-lg font-bold leading-tight text-primary">Which policy region is causing friction now</h3>
              <p className="mt-3 text-xs leading-6 text-on-surface-variant">
                Use this as an operator summary, not a raw engine dump. The goal is to see where review pressure is coming from without reading registry IDs.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Friction score</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.friction_score)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">False-review pressure across the current memory window.</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Automation efficiency</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.automation_efficiency)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">How often the system approved without needing manual review.</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Rule concentration</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.rule_concentration)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">Share of decisions dominated by the top firing rule.</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Surface imbalance</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.surface_imbalance)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">Share of routing dominated by one policy surface.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div>
          <p className="eyebrow">Context and insight</p>
          <h2 className="mt-2 text-3xl font-bold text-primary">Scan the environment</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-on-surface-variant">
            Feed history, integrity checks, forecast posture, and spatial context stay below the action layer so they
            support decisions instead of competing with them.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.86fr_1.14fr]">
          <div className="panel-muted p-6">
            <div className="mb-4 flex items-center gap-3">
              <ShieldAlert size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">Integrity preview</h3>
            </div>
            <div className="max-h-[300px] space-y-3 overflow-y-auto pr-1">
              {integrityPreview.length ? (
                integrityPreview.map((entry) => (
                  <div key={entry.id} className="rounded-[18px] border border-primary/8 bg-surface-container-low px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">
                      {entry.action === "duplicate_detected" ? "Duplicate block" : "Extension auth"} - {formatRelative(entry.created_at)}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                      Zone {humanizeSlug(entry.details?.zone || "system")} -{" "}
                      {(entry.details?.incident_triggers || entry.details?.fired_triggers || [])
                        .map(humanizeSlug)
                        .join(", ") || "No trigger list"}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">No recent duplicate or extension activity.</p>
              )}
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <AlertTriangle size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">Forecast horizon</h3>
            </div>
            <div className="space-y-3">
              {forecastEntries.map((entry) => {
                const tone = forecastTone(entry.band);

                return (
                  <div key={entry.city} className={`rounded-[20px] border bg-surface-container-low/80 p-4 ${tone.container}`}>
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary capitalize">{entry.city}</p>
                      <span className={`pill text-xs font-bold capitalize ${tone.pill}`}>{entry.band}</span>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-container-lowest">
                      <div
                        className={`h-full rounded-full transition-all ${tone.progress}`}
                        style={{ width: `${Math.min(100, entry.projected_risk * 100)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs leading-6 text-on-surface-variant">
                      Base {entry.base_risk.toFixed(2)} - Projected {entry.projected_risk.toFixed(2)} ({entry.active_incidents} active)
                    </p>
                  </div>
                );
              })}
              {!forecastEntries.length ? (
                <p className="text-sm text-on-surface-variant">No forecast entries match the current filters.</p>
              ) : null}
            </div>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1fr_1fr_0.9fr]">
          <div className="context-panel p-6">
            <div className="mb-4">
              <p className="eyebrow">Top friction rules</p>
              <h3 className="mt-2 text-lg font-bold text-primary">Rules causing review waste</h3>
            </div>
            <div className="space-y-3">
              {(policyHealth?.top_friction_rules || []).length ? (
                policyHealth.top_friction_rules.slice(0, 3).map((entry) => (
                  <div key={entry.rule_id} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{formatPolicyRule(entry.rule_id, "admin")}</p>
                      <span className="pill-subtle">{formatPercent(entry.friction_rate)}</span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">
                      {entry.false_review_count} false reviews across {entry.count} routed claims.
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">Rule friction will appear once more resolved history accumulates.</p>
              )}
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-4">
              <p className="eyebrow">Top friction surfaces</p>
              <h3 className="mt-2 text-lg font-bold text-primary">Policy regions that need sharper routing</h3>
            </div>
            <div className="space-y-3">
              {(policyHealth?.top_friction_surfaces || []).length ? (
                policyHealth.top_friction_surfaces.slice(0, 3).map((entry) => (
                  <div key={entry.surface} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{formatPolicySurface(entry.surface, "admin")}</p>
                      <span className="pill-subtle">{formatPercent(entry.friction_rate)}</span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">
                      {entry.false_review_count} false reviews across {entry.count} claim-created decisions.
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">Surface friction will appear once more replay evidence accumulates.</p>
              )}
            </div>
          </div>

          <div className="context-panel p-6">
            <div className="mb-4">
              <p className="eyebrow">Evidence mix</p>
              <h3 className="mt-2 text-lg font-bold text-primary">What kind of traffic shaped this reading</h3>
            </div>
            <div className="space-y-3">
              {Object.entries(trafficSourceCounts)
                .sort(([, a], [, b]) => Number(b) - Number(a))
                .slice(0, 4)
                .map(([source, count]) => {
                  const share = analytics?.decision_memory_summary?.claim_created_rows
                    ? Math.round((Number(count) / Number(analytics.decision_memory_summary.claim_created_rows)) * 100)
                    : 0;
                  return (
                    <div key={source} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold text-primary">{humanizeSlug(source)}</p>
                        <span className="pill-subtle">{share}%</span>
                      </div>
                      <p className="mt-2 text-sm text-on-surface-variant">{count} claim-created decisions in this source.</p>
                      {compactBar(share, "bg-primary")}
                    </div>
                  );
                })}
            </div>
          </div>
        </div>

        <DisruptionMap events={visibleEvents} city={selectedCity} />

        <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
          <EventPanel events={visibleEvents.slice(0, 4)} />

          <div className="context-panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <AlertTriangle size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">72h-7d Forecast cards</h3>
            </div>
            <ForecastCards city={selectedCity === "all" ? "delhi" : selectedCity} />
          </div>
        </div>
      </section>
    </div>
  );
}
