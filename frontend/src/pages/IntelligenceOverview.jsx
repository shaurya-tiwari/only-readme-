import { useEffect, useMemo, useState } from "react";
import { BrainCircuit, Clock3, TrendingUp } from "lucide-react";

import { analyticsApi } from "../api/analytics";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import SectionHeader from "../components/SectionHeader";
import { formatAudienceFactor, formatPolicyRule, formatPolicySurface } from "../utils/decisionNarrative";
import { formatDateTime, formatPercent, formatRelative, humanizeSlug } from "../utils/formatters";

function interpretLossRatio(value) {
  if (!Number.isFinite(Number(value))) {
    return {
      tone: "bg-surface-container-low text-on-surface",
      label: "Pending",
      message: "Loss ratio is not available yet.",
    };
  }

  const ratio = Number(value);
  if (ratio >= 150) {
    return {
      tone: "badge-error",
      label: "Pressure",
      message: "Claims are outpacing current premium volume. Treat this as a pricing or simulation stress signal.",
    };
  }
  if (ratio >= 100) {
    return {
      tone: "badge-pending",
      label: "Watch",
      message: "Claims and payouts are close to or above sustainable weekly pricing. Review premium calibration.",
    };
  }
  return {
    tone: "badge-active",
    label: "Stable",
    message: "Current payouts sit within the protection envelope implied by recent premium volume.",
  };
}

function interpretFraudRate(value) {
  const rate = Number(value || 0);
  if (rate >= 20) {
    return "Elevated suspicious activity. Review rule and model thresholds.";
  }
  if (rate >= 8) {
    return "Moderate fraud pressure. Watch manual review volume and duplicate patterns.";
  }
  return "Low flagged fraud pressure in the current window.";
}

function bandTone(band) {
  switch (band) {
    case "critical":
      return {
        container: "border-l-red-600 bg-surface-container-high/40",
        pill: "badge-error",
        progress: "bg-red-600",
      };
    case "elevated":
      return {
        container: "border-l-amber-600 bg-surface-container-high/40",
        pill: "badge-pending",
        progress: "bg-amber-600",
      };
    case "guarded":
      return {
        container: "border-l-blue-600 bg-surface-container-high/40",
        pill: "badge-guarded",
        progress: "bg-blue-600",
      };
    default:
      return {
        container: "border-l-emerald-600 bg-surface-container-high/40",
        pill: "badge-active",
        progress: "bg-emerald-600",
      };
  }
}

function barWidth(value) {
  return `${Math.max(4, Math.min(100, Number(value || 0)))}%`;
}

function signalSourceLabel(signalType, status) {
  const signal = humanizeSlug(signalType);
  if (!status) {
    return `${signal} source unknown`;
  }
  if (status.is_fallback) {
    return `Fallback ${signal.toLowerCase()} data`;
  }
  if (status.configured_source === "real" || String(status.latest_provider || "").startsWith("openweather")) {
    return `Live ${signal.toLowerCase()} data`;
  }
  return `Mock ${signal.toLowerCase()} data`;
}

function signalSourceTone(status) {
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

function signalFreshness(status) {
  if (!status?.captured_at) {
    return "No snapshot captured yet.";
  }
  const ageSeconds = Number(status.data_age_seconds);
  if (Number.isFinite(ageSeconds)) {
    if (ageSeconds < 60) {
      return "Updated under 1 minute ago.";
    }
    if (ageSeconds < 3600) {
      return `Updated ${Math.round(ageSeconds / 60)} minutes ago.`;
    }
  }
  return `Updated ${formatRelative(status.captured_at)}.`;
}

function summarizeSignalReadiness(statusMap) {
  const statuses = Object.values(statusMap || {});
  if (!statuses.length) {
    return {
      label: "Signal status pending",
      tone: "badge-pending",
      message: "No provider snapshots have been captured yet, so live-signal readiness cannot be verified.",
    };
  }

  const fallbackCount = statuses.filter((status) => status?.is_fallback).length;
  const liveCount = statuses.filter(
    (status) => status && !status.is_fallback && (status.configured_source === "real" || String(status.latest_provider || "").startsWith("openweather")),
  ).length;

  if (fallbackCount > 0) {
    return {
      label: "Backup data active",
      tone: "badge-pending",
      message: `${fallbackCount} signal feed${fallbackCount === 1 ? "" : "s"} is using backup data. The system is still operational, but this is a resilience state rather than a fully live reading.`,
    };
  }

  if (liveCount >= 2) {
    return {
      label: "Live signals ready",
      tone: "badge-active",
      message: `${liveCount} signal feeds are currently using live provider data. This is the strongest demo state for showing real disruption context feeding automated decisions.`,
    };
  }

  return {
    label: "Mixed runtime state",
    tone: "badge-guarded",
    message: "The system is running, but not every signal feed is live yet. This is acceptable for operations, but weaker for demo impact.",
  };
}

export default function IntelligenceOverview() {
  const [loading, setLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [signalHealth, setSignalHealth] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [locations, setLocations] = useState(null);
  const [models, setModels] = useState(null);
  const [loadErrors, setLoadErrors] = useState([]);
  const forecastReadings = useMemo(() => forecast || [], [forecast]);
  const topForecast = useMemo(
    () => [...forecastReadings].sort((a, b) => Number(b.projected_risk || 0) - Number(a.projected_risk || 0))[0] || null,
    [forecastReadings],
  );

  useEffect(() => {
    document.title = "System Intelligence | RideShield";
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const errors = [];
      try {
        const [analyticsRes, signalHealthRes, diagnosticsRes, citiesRes, modelsRes] = await Promise.allSettled([
          analyticsApi.adminOverview({ days: 14 }),
          healthApi.getSignals(),
          healthApi.getDiagnostics(),
          locationsApi.cities(),
          analyticsApi.models(),
        ]);

        if (analyticsRes.status === "fulfilled") {
          setAnalytics(analyticsRes.value.data);
        } else {
          errors.push("Analytics overview");
        }

        if (signalHealthRes.status === "fulfilled") {
          setSignalHealth(signalHealthRes.value.data);
        } else {
          errors.push("Signal health");
        }

        if (diagnosticsRes.status === "fulfilled") {
          setDiagnostics(diagnosticsRes.value.data);
        } else {
          errors.push("Diagnostics");
        }

        if (citiesRes.status === "fulfilled") {
          setLocations({ cities: citiesRes.value.data || [] });
        } else {
          errors.push("Locations");
        }

        if (modelsRes.status === "fulfilled") {
          setModels(modelsRes.value.data.models);
        } else {
          errors.push("Models");
        }

        setLoadErrors(errors);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  useEffect(() => {
    async function loadForecast() {
      setForecastLoading(true);
      try {
        const forecastRes = await analyticsApi.adminForecast();
        setForecast(forecastRes.data.next_week_forecast || []);
      } catch {
        setForecast([]);
      } finally {
        setForecastLoading(false);
      }
    }

    void loadForecast();
  }, []);

  if (loading) {
    return <div className="panel p-8 text-center text-on-surface-variant">Loading intelligence overview...</div>;
  }

  const scheduler = diagnostics?.scheduler;
  const lossRatio = interpretLossRatio(analytics?.loss_ratio);
  const fraudMeaning = interpretFraudRate(analytics?.fraud_rate);
  const citiesMonitored = (locations?.cities || []).length;
  const fraudModel = models?.fraud_model;
  const riskModel = models?.risk_model;
  const decisionMemory = analytics?.decision_memory_summary;
  const falseReviewSummary = analytics?.false_review_pattern_summary;
  const replaySummary = analytics?.policy_replay_summary;
  const policyHealth = analytics?.policy_health_summary;
  const dominantPatterns = falseReviewSummary?.dominant_patterns || [];
  const topFalseReviewDrivers = decisionMemory?.top_false_review_drivers || [];
  const trafficSourceCounts = decisionMemory?.traffic_source_counts || {};
  const signalSourceStatus = signalHealth?.signal_source_status || {};
  const signalReadiness = summarizeSignalReadiness(signalSourceStatus);

  return (
    <div className="space-y-10">
      {loadErrors.length > 0 && (
        <div className="rounded-[20px] border border-amber-400/30 bg-amber-500/10 px-5 py-4">
          <p className="text-sm font-semibold text-amber-300">Some sections failed to load</p>
          <p className="mt-1 text-sm text-amber-200/80">
            Unavailable: {loadErrors.join(", ")}. The rest of the page is showing live data.
          </p>
        </div>
      )}
      <section className="mb-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2">
              <BrainCircuit size={18} className="text-primary" />
              <p className="eyebrow">System intelligence</p>
            </div>
            <h1 className="mt-2 text-4xl font-bold tracking-tight text-primary">What changed, what is noisy, and what should be trusted next.</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-on-surface-variant">
              Reading layer for operators. Shows where the system is over-reviewing, which city is drifting toward pressure, and whether current policy changes are improving automation.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className={`pill ${scheduler?.enabled ? 'badge-active' : 'badge-pending'}`}>
              {scheduler?.enabled ? 'Scheduler active' : 'Scheduler disabled'}
            </span>
            <span className={`pill ${signalReadiness.tone}`}>{signalReadiness.label}</span>
            {topForecast ? (
              <span className="pill badge-guarded">
                Lead city: {humanizeSlug(topForecast.city)} ({topForecast.projected_risk.toFixed(2)} risk)
              </span>
            ) : null}
          </div>
        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Current readings"
          title="Current system-level indicators"
          description="Metrics should explain posture, not just fill space."
        />
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 p-6 decision-panel lg:col-span-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Loss ratio</p>
                <p className="mt-4 text-5xl font-bold text-primary">{formatPercent(analytics?.loss_ratio, 1)}</p>
              </div>
              <span className={`pill ${lossRatio.tone}`}>{lossRatio.label}</span>
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">{lossRatio.message}</p>
          </div>
          <div className="col-span-12 p-6 context-panel md:col-span-4">
            <p className="eyebrow">Fraud rate</p>
            <p className="mt-4 text-4xl font-bold text-primary">{formatPercent(analytics?.fraud_rate, 1)}</p>
            <p className="mt-3 text-sm leading-7 text-on-surface-variant">{fraudMeaning}</p>
          </div>
          <div className="col-span-12 p-6 context-panel md:col-span-4">
            <p className="eyebrow">Cities monitored</p>
            <p className="mt-4 text-4xl font-bold text-primary">{citiesMonitored}</p>
            <p className="mt-3 text-sm leading-7 text-on-surface-variant">
              {(locations?.cities || []).map((city) => city.display_name).join(", ")}
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-4">
          <div className="col-span-12 p-6 context-panel lg:col-span-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Risk model</p>
                <p className="mt-3 text-2xl font-bold text-primary">{riskModel?.version || "Unavailable"}</p>
              </div>
              <span className={`pill ${riskModel?.fallback_used ? "badge-pending" : "badge-active"}`}>
                {riskModel?.fallback_used ? "Fallback" : "Active"}
              </span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3 text-sm">
              <div>
                <p className="text-on-surface-variant">R²</p>
                <p className="mt-1 font-semibold text-primary">{riskModel?.r2_score != null ? Number(riskModel.r2_score).toFixed(3) : "--"}</p>
              </div>
              <div>
                <p className="text-on-surface-variant">MAE</p>
                <p className="mt-1 font-semibold text-primary">{riskModel?.mae != null ? Number(riskModel.mae).toFixed(3) : "--"}</p>
              </div>
              <div>
                <p className="text-on-surface-variant">Samples</p>
                <p className="mt-1 font-semibold text-primary">{riskModel?.n_samples || "--"}</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">
              This model informs premium posture and zone-level disruption risk. It shapes pricing and forecast posture rather than directly deciding payouts.
            </p>
          </div>

          <div className="col-span-12 p-6 context-panel lg:col-span-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Fraud model</p>
                <p className="mt-3 text-2xl font-bold text-primary">{fraudModel?.version || "Unavailable"}</p>
              </div>
              <span className={`pill ${fraudModel?.fallback_used ? "badge-pending" : "badge-active"}`}>
                {fraudModel?.fallback_used ? "Rule fallback" : "Hybrid active"}
              </span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-4 text-sm">
              <div>
                <p className="text-on-surface-variant">ROC AUC</p>
                <p className="mt-1 font-semibold text-primary">{fraudModel?.roc_auc != null ? Number(fraudModel.roc_auc).toFixed(3) : "--"}</p>
              </div>
              <div>
                <p className="text-on-surface-variant">Precision</p>
                <p className="mt-1 font-semibold text-primary">{fraudModel?.precision != null ? Number(fraudModel.precision).toFixed(3) : "--"}</p>
              </div>
              <div>
                <p className="text-on-surface-variant">Recall</p>
                <p className="mt-1 font-semibold text-primary">{fraudModel?.recall != null ? Number(fraudModel.recall).toFixed(3) : "--"}</p>
              </div>
              <div>
                <p className="text-on-surface-variant">Samples</p>
                <p className="mt-1 font-semibold text-primary">{fraudModel?.n_samples || "--"}</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">
              Fraud review remains hybrid. Rules are still the guardrail, while the model adds probability and factor context for suspicious claims.
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-6">
          <div className="col-span-12 context-panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <TrendingUp size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">Forecast bands</h3>
            </div>
            <div className="space-y-3">
              {forecastLoading ? (
                <p className="text-sm text-on-surface-variant">Loading forecast horizon...</p>
              ) : forecastReadings.map((entry) => {
                const tone = bandTone(entry.band);

                return (
                  <div key={entry.city} className={`rounded-[20px] border-l-4 p-5 transition-smooth hover:shadow-md ${tone.container}`}>
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <p className="font-semibold capitalize text-on-surface">{humanizeSlug(entry.city)}</p>
                      <span className={`pill text-xs font-bold capitalize ${tone.pill}`}>{entry.band}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-container-high">
                      <div className={`h-full rounded-full transition-all ${tone.progress}`} style={{ width: `${Math.min(100, entry.projected_risk * 100)}%` }} />
                    </div>
                    <p className="mt-2 text-xs text-on-surface-variant">
                      Base {entry.base_risk.toFixed(2)} - Projected {entry.projected_risk.toFixed(2)}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Decision memory"
          title="What the system learned from review history"
          description="Use replay and false-review patterns to decide where automation should expand next."
        />

        <div className="grid grid-cols-12 gap-5">
          <div className="col-span-12 context-panel p-6 lg:col-span-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Replay lift</p>
                <p className="mt-3 text-4xl font-bold text-primary">{replaySummary?.delayed_to_approved_count || 0}</p>
              </div>
              <span className="pill badge-active">{replaySummary?.match_rate || 0}% match</span>
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">
              Historical delayed claims that the current policy would now approve without human intervention.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Replay rows</p>
                <p className="mt-2 text-2xl font-bold text-primary">{replaySummary?.rows_replayed || 0}</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Approval drag</p>
                <p className="mt-2 text-2xl font-bold text-primary">{replaySummary?.approved_to_delayed_count || 0}</p>
              </div>
            </div>
          </div>

          <div className="col-span-12 context-panel p-6 lg:col-span-7">
            <p className="eyebrow">False-review concentration</p>
            <h3 className="mt-2 text-lg font-bold text-primary">The queue is still overspending effort in one band</h3>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {Object.entries(falseReviewSummary?.score_band_distribution || {})
                .sort(([, a], [, b]) => b - a)
                .map(([band, count]) => {
                  const share = falseReviewSummary?.false_review_count
                    ? Math.round((count / falseReviewSummary.false_review_count) * 100)
                    : 0;
                  return (
                    <div key={band} className="rounded-[20px] border border-primary/8 bg-surface-container-low/80 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold text-primary">{band.replaceAll("_", ".")}</p>
                        <span className="pill-subtle">{share}%</span>
                      </div>
                      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-container-high">
                        <div className="h-full rounded-full bg-primary transition-all" style={{ width: barWidth(share) }} />
                      </div>
                      <p className="mt-2 text-xs text-on-surface-variant">{count} false reviews in this score band.</p>
                    </div>
                  );
                })}
            </div>
            <div className="mt-5 rounded-[20px] border border-primary/8 bg-surface-container-low/70 p-4">
              <p className="text-sm font-semibold text-primary">Current interpretation</p>
              <p className="mt-2 text-sm leading-7 text-on-surface-variant">
                {falseReviewSummary?.false_review_count
                  ? `${Math.round(((falseReviewSummary.score_band_distribution?.["0.60_0.65"] || 0) / falseReviewSummary.false_review_count) * 100)}% of false reviews still sit in the 0.60-0.65 band, and all observed false reviews remain below INR 125.`
                  : "Decision memory has not accumulated enough false-review evidence yet."}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-5">
          <div className="col-span-12 context-panel p-6 lg:col-span-6">
            <p className="eyebrow">Dominant patterns</p>
            <h3 className="mt-2 text-lg font-bold text-primary">Which signal mixes are wasting review effort</h3>
            <div className="mt-5 space-y-3">
              {dominantPatterns.length ? (
                dominantPatterns.slice(0, 4).map((pattern, index) => (
                  <div key={`${pattern.flags.join("-") || "no-flags"}-${index}`} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">
                        {pattern.flags.length ? pattern.flags.map(humanizeSlug).join(" + ") : "No flags"}
                      </p>
                      <span className="pill-subtle">{pattern.share}%</span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">{pattern.count} false-review cases in the current memory window.</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">No dominant false-review patterns are available yet.</p>
              )}
            </div>
          </div>

          <div className="col-span-12 context-panel p-6 lg:col-span-6">
            <p className="eyebrow">Memory health</p>
            <h3 className="mt-2 text-lg font-bold text-primary">How much evidence the system actually has</h3>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Logged decisions</p>
                <p className="mt-2 text-2xl font-bold text-primary">{decisionMemory?.window_logged_decisions || 0}</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Resolved labels</p>
                <p className="mt-2 text-2xl font-bold text-primary">{decisionMemory?.resolved_labels || 0}</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">False reviews</p>
                <p className="mt-2 text-2xl font-bold text-primary">{decisionMemory?.false_review_count || 0}</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Manual override rate</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(decisionMemory?.manual_override_rate)}</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">
              This is the evidence base for later calibration. The goal is not to lower thresholds blindly. The goal is to shrink manual review only where stored outcomes prove the queue is being overly cautious.
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-5">
          <div className="col-span-12 context-panel p-6 lg:col-span-5">
            <p className="eyebrow">Policy health</p>
            <h3 className="mt-2 text-lg font-bold text-primary">How concentrated and friction-heavy the policy has become</h3>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Friction score</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.friction_score)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">False-review pressure across all logged claim-created decisions.</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Automation efficiency</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.automation_efficiency)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">Share of claim-created decisions that auto-approved immediately.</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Rule concentration</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.rule_concentration)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">How much one rule dominates the current decision window.</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Surface imbalance</p>
                <p className="mt-2 text-2xl font-bold text-primary">{formatPercent(policyHealth?.surface_imbalance)}</p>
                <p className="mt-2 text-xs text-on-surface-variant">How much one policy surface dominates routing right now.</p>
              </div>
            </div>
          </div>

          <div className="col-span-12 context-panel p-6 lg:col-span-7">
            <p className="eyebrow">Traffic-source reading</p>
            <h3 className="mt-2 text-lg font-bold text-primary">What kind of evidence is driving the current analytics</h3>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {Object.entries(trafficSourceCounts)
                .sort(([, a], [, b]) => Number(b) - Number(a))
                .map(([source, count]) => {
                  const share = decisionMemory?.claim_created_rows
                    ? Math.round((Number(count) / Number(decisionMemory.claim_created_rows)) * 100)
                    : 0;
                  return (
                    <div key={source} className="rounded-[20px] border border-primary/8 bg-surface-container-low/80 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold text-primary">{humanizeSlug(source)}</p>
                        <span className="pill-subtle">{share}%</span>
                      </div>
                      <p className="mt-2 text-sm text-on-surface-variant">{count} claim-created rows in the current memory window.</p>
                      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-container-high">
                        <div className="h-full rounded-full bg-primary transition-all" style={{ width: barWidth(share) }} />
                      </div>
                    </div>
                  );
                })}
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">
              Baseline, simulation pressure, scenario, and replay-amplified traffic should never be treated as one bucket.
              This split is the guardrail that keeps calibration from learning the wrong lesson too quickly.
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-5">
          <div className="col-span-12 context-panel p-6 lg:col-span-5">
            <p className="eyebrow">Live signal status</p>
            <h3 className="mt-2 text-lg font-bold text-primary">Which provider story is currently active</h3>
            <div className="mt-5 space-y-3">
              {["weather", "aqi", "traffic", "platform"].map((signalType) => {
                const status = signalSourceStatus[signalType];
                return (
                  <div key={signalType} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{signalSourceLabel(signalType, status)}</p>
                      <span className={`pill ${signalSourceTone(status)}`}>
                        {status?.is_fallback ? "Fallback" : humanizeSlug(status?.configured_source || "unknown")}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">
                      Provider {humanizeSlug(status?.latest_provider || status?.configured_source || "unknown")}{" "}
                      {status?.latency_ms != null ? `| ${status.latency_ms}ms fetch` : ""}
                    </p>
                    <p className="mt-1 text-xs text-on-surface-variant">{signalFreshness(status)}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="col-span-12 context-panel p-6 lg:col-span-6">
            <p className="eyebrow">Top false-review drivers</p>
            <h3 className="mt-2 text-lg font-bold text-primary">What currently wastes review effort</h3>
            <div className="mt-5 space-y-3">
              {topFalseReviewDrivers.length ? (
                topFalseReviewDrivers.map((driver) => (
                  <div key={driver.label} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{formatAudienceFactor(driver.label, "admin")}</p>
                      <span className="pill-subtle">{driver.share}%</span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">{driver.count} false-review labels include this driver.</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">False-review drivers will appear once more resolved labels accumulate.</p>
              )}
            </div>
          </div>

          <div className="col-span-12 context-panel p-6 lg:col-span-7">
            <p className="eyebrow">Policy reading</p>
            <h3 className="mt-2 text-lg font-bold text-primary">What the current replay is saying</h3>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Replay approvals</p>
                <p className="mt-2 text-2xl font-bold text-primary">{replaySummary?.replay_route_counts?.approved || 0}</p>
              </div>
              <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                <p className="text-sm text-on-surface-variant">Replay delayed</p>
                <p className="mt-2 text-2xl font-bold text-primary">{replaySummary?.replay_route_counts?.delayed || 0}</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-7 text-on-surface-variant">
              Current replay lifts {replaySummary?.delayed_to_approved_count || 0} old delayed claims into approval while dragging {replaySummary?.approved_to_delayed_count || 0} previously approved claims back to review. That tradeoff should stay visible before any threshold change is promoted.
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-5">
          <div className="col-span-12 context-panel p-6 lg:col-span-6">
            <p className="eyebrow">Top friction rules</p>
            <h3 className="mt-2 text-lg font-bold text-primary">Which policy rules are doing the most bad operational work</h3>
            <div className="mt-5 space-y-3">
              {(policyHealth?.top_friction_rules || []).length ? (
                policyHealth.top_friction_rules.map((entry) => (
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
                <p className="text-sm text-on-surface-variant">Rule friction will appear after more resolved decision-memory evidence accumulates.</p>
              )}
            </div>
          </div>

          <div className="col-span-12 context-panel p-6 lg:col-span-6">
            <p className="eyebrow">Top friction surfaces</p>
            <h3 className="mt-2 text-lg font-bold text-primary">Which policy surfaces need sharper definitions next</h3>
            <div className="mt-5 space-y-3">
              {(policyHealth?.top_friction_surfaces || []).length ? (
                policyHealth.top_friction_surfaces.map((entry) => (
                  <div key={entry.surface} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary">{formatPolicySurface(entry.surface, "admin")}</p>
                      <span className="pill-subtle">{formatPercent(entry.friction_rate)}</span>
                    </div>
                    <p className="mt-2 text-sm text-on-surface-variant">
                      {entry.false_review_count} false reviews across {entry.count} claim-created decisions in this surface.
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">Surface friction will appear after more replay and resolved-label history accumulates.</p>
              )}
            </div>
          </div>
        </div>
      </section>


    </div>
  );
}
