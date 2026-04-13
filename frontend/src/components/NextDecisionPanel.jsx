import clsx from "clsx";

import { adminIncidentNarrative } from "../utils/decisionNarrative";
import { formatCurrency, formatReviewWindow, formatScore, humanizeSlug, statusPill } from "../utils/formatters";

function confidenceTone(band) {
  if (band === "high") {
    return "badge-active";
  }
  if (band === "moderate") {
    return "badge-guarded";
  }
  return "badge-pending";
}

/**
 * Admin-facing next-decision panel — surfaces the top grouped incident
 * that requires manual review, with fraud score, payout at risk, and
 * a contextual narrative.
 *
 * Extracted from AdminPanel.jsx to keep the page file focused on data
 * orchestration rather than sub-component layout.
 *
 * @param {{ incident: object|null }} props
 */
export default function NextDecisionPanel({ incident }) {
  if (!incident) {
    return (
      <div className="decision-panel p-6">
        <p className="eyebrow">Next decision</p>
        <h3 className="mt-3 text-2xl font-bold text-primary">No delayed claim needs action right now.</h3>
        <p className="mt-4 text-sm leading-7 text-on-surface-variant">
          The review queue is clear. Logs, incidents, and forecast cards below are supporting context rather than active
          blockers.
        </p>
      </div>
    );
  }

  const triggerTypes = Array.isArray(incident.trigger_types)
    ? incident.trigger_types
    : incident.trigger_type
      ? [incident.trigger_type]
      : [];
  const topFactors = Array.isArray(incident.top_factors) ? incident.top_factors.slice(0, 3) : [];
  const fraudProbability =
    incident.max_fraud_probability === null || incident.max_fraud_probability === undefined
      ? null
      : Math.round(Number(incident.max_fraud_probability || 0) * 100);
  const narrative = adminIncidentNarrative(incident);

  return (
    <div className="decision-panel p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Next decision</p>
          <h3 className="mt-3 text-2xl font-bold text-primary">{incident.worker_name}</h3>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className={statusPill(incident.status)}>{humanizeSlug(incident.status)}</span>
          <span className={clsx("pill", confidenceTone(incident.decision_confidence_band))}>
            Confidence {humanizeSlug(incident.decision_confidence_band)}
          </span>
        </div>
      </div>

      <p className="mt-4 text-sm leading-7 text-on-surface-variant">
        {(triggerTypes.length ? triggerTypes.map(humanizeSlug).join(", ") : "No trigger context")} -{" "}
        {humanizeSlug(incident.zone || "zone")}
      </p>

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <div className="rounded-[20px] border border-primary/10 bg-surface-container-high/75 p-4">
          <p className="text-sm text-on-surface-variant">Decision confidence</p>
          <p className="mt-2 text-2xl font-bold text-primary">{formatScore(incident.max_decision_confidence)}</p>
          <p className="mt-2 text-xs text-on-surface-variant">
            Signal confidence is {humanizeSlug(incident.decision_confidence_band)} for this review recommendation.
          </p>
        </div>
        <div className="rounded-[20px] border border-primary/10 bg-surface-container-high/75 p-4">
          <p className="text-sm text-on-surface-variant">Payout at risk</p>
          <p className="mt-2 text-2xl font-bold text-primary">
            {formatCurrency(incident.payout_risk || incident.total_calculated_payout)}
          </p>
          <p className="mt-2 text-xs text-on-surface-variant">Gross payout {formatCurrency(incident.total_calculated_payout)}</p>
        </div>
        <div className="rounded-[20px] border border-primary/10 bg-surface-container-high/75 p-4">
          <p className="text-sm text-on-surface-variant">Wait window</p>
          <p className="mt-2 text-2xl font-bold text-primary">{formatReviewWindow(incident.hours_until_deadline)}</p>
          <p className="mt-2 text-xs text-on-surface-variant">
            Queue has already held this incident for the highest-pressure claim in the group.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-[18px] border border-primary/10 bg-surface-container-low p-4">
          <p className="text-sm text-on-surface-variant">Fraud probability</p>
          <p className="mt-2 text-lg font-semibold text-primary">{fraudProbability === null ? "--" : `${fraudProbability}%`}</p>
          <p className="mt-2 text-xs text-on-surface-variant">
            {incident.fraud_model_version || "rule-based"} {incident.fraud_fallback_used ? "- fallback" : "- hybrid active"}
          </p>
        </div>
        <div className="rounded-[18px] border border-primary/10 bg-surface-container-low p-4">
          <p className="text-sm text-on-surface-variant">Review pattern</p>
          <p className="mt-2 text-lg font-semibold text-primary">{narrative.patternLabel}</p>
          <p className="mt-2 text-xs leading-6 text-on-surface-variant">{narrative.summary}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="pill-neutral">Primary: {narrative.primary}</span>
            {narrative.evidence.map((factor) => (
              <span key={factor} className="pill-subtle">
                {factor}
              </span>
            ))}
          </div>
          {incident.uncertainty_case ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="pill-subtle">Uncertainty: {humanizeSlug(incident.uncertainty_case)}</span>
            </div>
          ) : topFactors.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {topFactors.map((factor) => (
                <span key={factor.factor} className="pill-neutral">
                  {factor.label}
                </span>
              ))}
            </div>
          ) : (
            <span className="mt-2 inline-flex text-sm text-on-surface-variant">No ML factors available.</span>
          )}
        </div>
      </div>

      <div className="mt-5 rounded-[20px] border border-primary/10 bg-primary/5 p-4">
        <p className="text-sm font-semibold text-primary">Why this is surfaced first</p>
        <p className="mt-3 text-sm leading-7 text-on-surface-variant">
          {incident.priority_reason || "This grouped incident has the strongest current review pressure."} Resolve the
          manual decision here before working through passive logs and forecast context below.
        </p>
      </div>
    </div>
  );
}
