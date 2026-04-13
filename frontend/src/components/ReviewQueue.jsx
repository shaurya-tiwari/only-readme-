import clsx from "clsx";
import { Check, X } from "lucide-react";

import { groupClaimsByIncident } from "../utils/claimGroups";
import { adminIncidentNarrative } from "../utils/decisionNarrative";
import {
  formatCurrency,
  formatHours,
  formatReviewWindow,
  formatScore,
  humanizeSlug,
  statusPill,
} from "../utils/formatters";

function urgencyTone(band) {
  if (band === "critical") {
    return {
      card: "border-l-red-400/90 bg-[linear-gradient(135deg,rgba(147,0,10,0.12),rgba(11,19,38,0.96))]",
      badge: "badge-error",
      label: "Critical",
    };
  }
  if (band === "warning") {
    return {
      card: "border-l-amber-400/90 bg-[linear-gradient(135deg,rgba(180,120,0,0.10),rgba(11,19,38,0.96))]",
      badge: "badge-pending",
      label: "Watch",
    };
  }
  return {
    card: "border-l-primary/70 bg-surface-container-low/90",
    badge: "badge-active",
    label: "Steady",
  };
}

function confidenceTone(band) {
  if (band === "high") {
    return "badge-active";
  }
  if (band === "moderate") {
    return "badge-guarded";
  }
  return "badge-pending";
}

export default function ReviewQueue({ claims = [], resolvingId, onResolve, highLoadMode = false, highLoadThreshold = 0 }) {
  const incidents = groupClaimsByIncident(claims, { bucketMinutes: 90 });
  const hasActiveQueue = incidents.length > 0;

  return (
    <div className="decision-panel p-6">
      <div className="mb-5">
        <div className="flex flex-wrap items-center gap-3">
          <p className="eyebrow">Admin workflow</p>
          {highLoadMode ? <span className="pill badge-pending">High load mode active</span> : null}
        </div>
        <h3 className="mt-2 text-2xl font-bold text-primary">Manual review queue</h3>
        <p className="mt-2 text-sm leading-6 text-on-surface-variant">
          Delayed claims are grouped by incident so the reviewer sees one disruption narrative with the underlying claim
          actions still exposed.
        </p>
        {highLoadMode ? (
          <p className="mt-2 text-xs leading-6 text-on-surface-variant">
            Review backlog has crossed the operating threshold{highLoadThreshold ? ` of ${highLoadThreshold}` : ""}, so low-risk approvals should be cleared faster.
          </p>
        ) : null}
      </div>

      <div className="space-y-3">
        {hasActiveQueue ? (
          incidents.map((incident) => (
            (() => {
              const narrative = adminIncidentNarrative(incident);
              return (
                <div
                  key={incident.id}
                  className={clsx(
                    "rounded-[24px] border border-primary/10 border-l-4 p-4 shadow-[0_18px_40px_rgba(7,10,20,0.28)] transition-smooth",
                    urgencyTone(incident.urgency_band).card,
                  )}
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className={statusPill(incident.status)}>{humanizeSlug(incident.status)}</span>
                        <span className={clsx("pill", urgencyTone(incident.urgency_band).badge)}>
                          {urgencyTone(incident.urgency_band).label} queue
                        </span>
                        <p className="text-sm font-semibold text-primary">{incident.worker_name}</p>
                      </div>
                      <p className="mt-2 text-sm text-on-surface-variant">
                        {incident.trigger_types.map(humanizeSlug).join(", ")} - {humanizeSlug(incident.zone)}
                      </p>
                      <p className="mt-1 text-xs text-on-surface-variant">
                        {incident.claim_count > 1
                          ? `${incident.claim_count} linked claims in one disruption incident`
                          : "Single delayed claim"}
                      </p>
                    </div>

                    <div className="text-right text-sm">
                      <p className="font-semibold text-primary">{formatCurrency(incident.payout_risk || incident.total_calculated_payout)}</p>
                      <p className="mt-1 text-on-surface-variant">{formatReviewWindow(incident.hours_until_deadline)}</p>
                    </div>
                  </div>

                  <div className="mb-4 grid gap-3 text-sm sm:grid-cols-4">
                    <div>
                      <p className="text-on-surface-variant">Wait time</p>
                      <p className="mt-2 font-semibold text-primary">{formatHours(incident.hours_waiting)}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-variant">Fraud score</p>
                      <p className="mt-2 font-semibold text-primary">{formatScore(incident.max_fraud_score)}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-variant">Final score</p>
                      <p className="mt-2 font-semibold text-primary">{formatScore(incident.avg_final_score)}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-variant">Confidence</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className={clsx("pill", confidenceTone(incident.decision_confidence_band))}>
                          {humanizeSlug(incident.decision_confidence_band)}
                        </span>
                        <span className="font-semibold text-primary">{formatScore(incident.max_decision_confidence)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mb-4 rounded-[18px] border border-primary/8 bg-surface-container-high/75 p-3">
                    <div className="flex flex-wrap items-center gap-3 text-xs text-on-surface-variant">
                      <span className="font-semibold text-primary">
                        {incident.fraud_model_version || "rule-based"} {incident.fraud_fallback_used ? "- fallback" : "- hybrid active"}
                      </span>
                      <span>
                        Fraud probability {incident.max_fraud_probability === null || incident.max_fraud_probability === undefined
                          ? "--"
                          : `${Math.round(Number(incident.max_fraud_probability || 0) * 100)}%`}
                      </span>
                      <span>Priority {incident.priority_reason || "Review queue"}</span>
                    </div>
                    <div className="mt-3 rounded-[16px] border border-primary/8 bg-surface-container-low/90 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-on-surface-variant">Review pattern</p>
                          <p className="mt-2 text-sm font-semibold text-primary">{narrative.patternLabel}</p>
                        </div>
                        {incident.uncertainty_case ? (
                          <span className="pill-subtle">{humanizeSlug(incident.uncertainty_case)}</span>
                        ) : null}
                      </div>
                      <p className="mt-3 text-sm leading-6 text-on-surface-variant">{narrative.summary}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="pill-neutral">Primary: {narrative.primary}</span>
                        {narrative.evidence.map((factor) => (
                          <span key={factor} className="pill-subtle">
                            {factor}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      {incident.claims.map((claim) => (
                        <span key={claim.id} className="pill-neutral">
                          {humanizeSlug(claim.trigger_type)} - {claim.id.slice(0, 6)}
                        </span>
                      ))}
                    </div>

                    <div className="flex flex-wrap gap-3">
                      {incident.claims.map((claim) => (
                        <div key={claim.id} className="flex flex-wrap gap-3">
                          <button
                            type="button"
                            disabled={resolvingId === claim.id}
                            onClick={() => onResolve(claim.id, "approve")}
                            className="button-primary !rounded-xl !px-4 !py-2 text-sm"
                          >
                            <Check size={16} />
                            Approve {claim.id.slice(0, 6)}
                          </button>
                          <button
                            type="button"
                            disabled={resolvingId === claim.id}
                            onClick={() => onResolve(claim.id, "reject")}
                            className="button-secondary !rounded-xl !px-4 !py-2 text-sm"
                          >
                            <X size={16} />
                            Reject {claim.id.slice(0, 6)}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })()
          ))
        ) : (
          <div className="rounded-[24px] border border-primary/12 bg-surface-container-high/75 p-5 shadow-[inset_0_1px_0_rgba(105,248,233,0.05)]">
            <p className="text-sm font-semibold text-primary">No delayed claims waiting for review.</p>
            <p className="mt-2 text-sm leading-6 text-on-surface">
              The current filters do not surface any blocked incidents. The next decision panel should stay quiet until
              a reviewable claim appears.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
