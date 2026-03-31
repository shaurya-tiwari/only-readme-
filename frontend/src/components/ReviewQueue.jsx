import { Check, X } from "lucide-react";

import { groupClaimsByIncident } from "../utils/claimGroups";
import { formatCurrency, formatRelative, formatScore, humanizeSlug, statusPill } from "../utils/formatters";

export default function ReviewQueue({ claims = [], resolvingId, onResolve }) {
  const incidents = groupClaimsByIncident(claims, { bucketMinutes: 90 });

  return (
    <div className="panel p-6">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Admin workflow</p>
        <h3 className="mt-1 text-2xl font-bold">Manual review queue</h3>
      </div>
      <div className="space-y-3">
        {incidents.length ? (
          incidents.map((incident) => (
            <div key={incident.id} className="rounded-2xl bg-black/[0.03] p-4">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-3">
                    <span className={statusPill(incident.status)}>{humanizeSlug(incident.status)}</span>
                    <p className="text-sm font-semibold">{incident.worker_name}</p>
                  </div>
                  <p className="mt-2 text-sm text-ink/60">
                    {incident.trigger_types.map(humanizeSlug).join(", ")} · {humanizeSlug(incident.zone)}
                  </p>
                  <p className="mt-1 text-xs text-ink/45">
                    {incident.claim_count > 1 ? `${incident.claim_count} linked claims in one disruption incident` : "Single delayed claim"}
                  </p>
                </div>
                <div className="text-right text-sm">
                  <p className="font-semibold">{formatCurrency(incident.total_calculated_payout)}</p>
                  <p className="text-ink/45">{formatRelative(incident.review_deadline)}</p>
                </div>
              </div>
              <div className="mb-4 grid gap-3 text-sm sm:grid-cols-3">
                <div>
                  <p className="text-ink/45">Fraud score</p>
                  <p className="font-semibold">{formatScore(incident.max_fraud_score)}</p>
                </div>
                <div>
                  <p className="text-ink/45">Final score</p>
                  <p className="font-semibold">{formatScore(incident.avg_final_score)}</p>
                </div>
                <div>
                  <p className="text-ink/45">Overdue</p>
                  <p className="font-semibold">{incident.overdue_count ? "Yes" : "No"}</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {incident.claims.map((claim) => (
                    <span key={claim.id} className="pill bg-white text-ink/65">
                      {humanizeSlug(claim.trigger_type)} · {claim.id.slice(0, 6)}
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
          ))
        ) : (
          <p className="text-sm text-ink/55">No delayed claims waiting for review.</p>
        )}
      </div>
    </div>
  );
}
