import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, ShieldAlert } from "lucide-react";
import toast from "react-hot-toast";

import { analyticsApi } from "../api/analytics";
import { claimsApi } from "../api/claims";
import { eventsApi } from "../api/events";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import DisruptionMap from "../components/DisruptionMap";
import ErrorState from "../components/ErrorState";
import EventPanel from "../components/EventPanel";

import KpiTile from "../components/KpiTile";
import ModelHealthBadge from "../components/ModelHealthBadge";
import NextDecisionPanel from "../components/NextDecisionPanel";
import ReviewQueue from "../components/ReviewQueue";
import { groupClaimsByIncident } from "../utils/claimGroups";
import { formatAudienceFactor } from "../utils/decisionNarrative";
import { formatCurrency, formatPercent, formatRelative, humanizeSlug } from "../utils/formatters";

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

const BACKGROUND_REFRESH_DELAY_MS = 3000;

export default function AdminPanel() {
  const [selectedCity, setSelectedCity] = useState("all");
  const [selectedZone, setSelectedZone] = useState("all");
  const [cityOptions, setCityOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [loadWarnings, setLoadWarnings] = useState([]);
  const [claimStats, setClaimStats] = useState(null);
  const [payoutStats, setPayoutStats] = useState(null);
  const [queue, setQueue] = useState(null);
  const [events, setEvents] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [signalHealth, setSignalHealth] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);
  const backgroundRefreshTimer = useState({ current: null })[0];

  useEffect(() => {
    document.title = "Admin Panel | RideShield";
  }, []);

  useEffect(() => {
    load();
    loadCities();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadForecast();
  }, []);

  async function loadCities() {
    try {
      const response = await locationsApi.cities();
      setCityOptions(response.data || []);
    } catch {
      setCityOptions([]);
    }
  }

  /**
   * Lightweight background refresh â€” only fetches stats after a resolve.
   * The queue itself is updated optimistically in handleResolve, so we
   * don't need to re-fetch the 34-46s review-queue endpoint here.
   */
  function scheduleBackgroundRefresh() {
    clearTimeout(backgroundRefreshTimer.current);
    backgroundRefreshTimer.current = setTimeout(async () => {
      try {
        const claimsRes = await claimsApi.stats({ days: 14 });
        setClaimStats(claimsRes.data);
      } catch {
        // silent â€” local state is already correct
      }
    }, BACKGROUND_REFRESH_DELAY_MS);
  }

  async function loadForecast() {
    setForecastLoading(true);
    try {
      const response = await analyticsApi.adminForecast();
      setForecast(response.data?.next_week_forecast || []);
    } catch {
      setForecast([]);
    } finally {
      setForecastLoading(false);
    }
  }

  async function load() {
    setLoading(true);
    setLoadError(null);
    setLoadWarnings([]);
    try {
      // Phase 1: Critical path â€” truly fast endpoints only
      // stats (~585ms), payout stats (~560ms), signals (~676ms)
      const criticalResults = await Promise.allSettled([
        claimsApi.stats({ days: 14 }),
        payoutsApi.stats({ days: 14 }),
        healthApi.getSignals(),
      ]);

      const [claimsRes, payoutsRes, signalsRes] = criticalResults;

      const nextWarnings = [];
      const readData = (result, label, fallback = null) => {
        if (result.status === "fulfilled") {
          return result.value.data;
        }
        nextWarnings.push(label);
        return fallback;
      };

      const claimsData = readData(claimsRes, "claims summary", claimStats);
      const payoutsData = readData(payoutsRes, "payout summary", payoutStats);
      const signalHealthData = readData(signalsRes, "signal runtime", signalHealth);

      setClaimStats(claimsData);
      setPayoutStats(payoutsData);
      setSignalHealth(signalHealthData);
      setLoadWarnings(nextWarnings);
    } catch (err) {
      setLoadError(err?.response?.data?.detail || err?.message || "Failed to load admin panel data.");
    } finally {
      setLoading(false);
    }

    // Phase 2: Deferred path â€” endpoints that are slow under contention
    // queue (~3-46s), events/active (~14-50s), events/history (~11-64s), admin-overview (~15s)
    try {
      const deferredResults = await Promise.allSettled([
        claimsApi.queue(),
        eventsApi.active(),
        eventsApi.history({ days: 14, limit: 20 }),
        analyticsApi.adminOverview({ days: 14 }),
      ]);

      const [queueRes, eventsRes, historyRes, analyticsRes] = deferredResults;
      const deferredWarnings = [];

      const readDeferred = (result, label, fallback = null) => {
        if (result.status === "fulfilled") {
          return result.value.data;
        }
        deferredWarnings.push(label);
        return fallback;
      };

      const queueData = readDeferred(queueRes, "review queue", queue);
      const activeEventsData = readDeferred(eventsRes, "active incidents", { events: [] });
      const historyData = readDeferred(historyRes, "incident history", { events: [] });
      const analyticsData = readDeferred(analyticsRes, "admin analytics", analytics);

      setQueue(queueData);
      setEvents([...(activeEventsData?.events || []), ...(historyData?.events || []).slice(0, 6)]);
      setAnalytics(analyticsData);

      if (deferredWarnings.length) {
        setLoadWarnings((current) => [...current, ...deferredWarnings]);
      }
    } catch {
      // Phase 2 failures don't kill the page â€” KPIs are already visible
    }
  }

  async function handleResolve(claimId, decision) {
    setResolvingId(claimId);

    // Optimistic: remove the claim from queue immediately so the UI feels instant
    // even when the backend takes 28-60s under contention.
    let previousQueue = null;
    setQueue((current) => {
      previousQueue = current;
      if (!current?.claims) {
        return current;
      }
      const nextClaims = current.claims.filter((claim) => claim.id !== claimId);
      return {
        ...current,
        claims: nextClaims,
        total_delayed: nextClaims.length,
      };
    });
    toast.success(`Claim ${decision === "reject" ? "rejected" : "approved"}.`);

    try {
      await claimsApi.resolve(claimId, {
        decision,
        reviewed_by: "admin_panel",
        reason: decision === "reject" ? "Rejected from admin panel." : "Approved from admin panel.",
      });
      scheduleBackgroundRefresh();
    } catch (error) {
      const detail = error?.response?.data?.detail || "";
      if (error?.response?.status === 400 && String(detail).includes("not 'delayed'")) {
        // Claim was already resolved â€” optimistic removal was correct
        toast.success("Claim was already resolved.");
        scheduleBackgroundRefresh();
        return;
      }
      // Backend failed â€” restore the claim to the queue
      if (previousQueue) {
        setQueue(previousQueue);
      }
      toast.error(detail || "Failed to resolve claim. Restored to queue.");
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
  const forecastEntries = (forecast || []).filter(
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

  const signalSourceStatus = signalHealth?.signal_source_status || {};

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
            <span className={`pill ${queue === null ? "badge-pending" : queuePressure.tone}`}>
              {queue === null ? "Loading queue..." : queuePressure.label}
            </span>
            {queue?.high_load_mode ? <span className="pill badge-pending">High load mode active</span> : null}
            <span className="pill-subtle">{queue === null ? "-- incidents" : `${filteredQueueIncidents.length} incidents`}</span>
            <span className="pill-subtle">{queue === null ? "-- overdue" : `${queueOverdueCount} overdue`}</span>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.18fr_0.82fr]">
          <ReviewQueue
            claims={filteredQueueClaims}
            isLoading={queue === null}
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
            <p className="eyebrow">Signal runtime</p>
            <h3 className="mt-2 text-lg font-bold leading-tight text-primary">Are signals alive?</h3>
            <div className="mt-4 flex flex-wrap gap-3">
              {["weather", "aqi", "traffic", "platform"].map((signalType) => {
                const status = signalSourceStatus[signalType];
                return (
                  <div key={signalType} className="flex items-center gap-2 rounded-full border border-primary/10 bg-surface-container-low/80 px-4 py-2">
                    <span className={`h-2 w-2 shrink-0 rounded-full ${!status ? 'bg-amber-500' : status.is_fallback ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                    <span className="text-sm font-semibold text-primary">{humanizeSlug(signalType)}</span>
                    <span className={`pill text-xs ${sourceTone(status)}`}>
                      {!status ? 'Unknown' : status.is_fallback ? 'Fallback' : humanizeSlug(status.configured_source || 'mock')}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          {/* Calibration Watch, Policy Health â†’ moved to Intelligence Overview */}
        </div>
      </section>


      {loadWarnings.length ? (
        <section className="panel-muted border border-amber-300/20 p-4">
          <p className="text-sm font-semibold text-primary">Partial admin data load</p>
          <p className="mt-1 text-sm text-on-surface-variant">
            The panel loaded with cached or reduced data because these sections did not respond in time:
            {" "}
            {loadWarnings.join(", ")}.
          </p>
        </section>
      ) : null}

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
                if (forecastLoading) {
                  return null;
                }
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
                <p className="text-sm text-on-surface-variant">
                  {forecastLoading ? "Loading forecast horizon..." : "No forecast entries match the current filters."}
                </p>
              ) : null}
            </div>
          </div>
        </div>

        {/* Friction Rules, Friction Surfaces, Evidence Mix â†’ moved to Intelligence Overview */}

        <DisruptionMap events={visibleEvents} city={selectedCity} />

        <EventPanel events={visibleEvents.slice(0, 6)} />
      </section>
    </div>
  );
}
