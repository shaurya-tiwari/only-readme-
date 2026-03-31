import { groupClaimsByIncident } from "../utils/claimGroups";
import { formatCurrency, formatDateTime, formatScore, humanizeSlug, statusPill } from "../utils/formatters";

function reasoningLine(status) {
  if (status === "approved") {
    return "Approved because disruption evidence stayed strong and fraud risk stayed low.";
  }
  if (status === "delayed") {
    return "Delayed because the incident looks real but the system wants an admin decision before payout.";
  }
  return "Rejected because the disruption or worker evidence was not strong enough for payout.";
}

export default function ClaimList({ claims = [], onSelect, compact = false }) {
  if (!claims.length) {
    return <p className="text-sm text-ink/55">No claims found for this view.</p>;
  }

  const incidents = groupClaimsByIncident(claims, { bucketMinutes: 90 });

  return (
    <div className="space-y-3">
      {incidents.map((incident) => (
        <button
          key={incident.id}
          type="button"
          onClick={() => onSelect?.(incident.claims[0])}
          className="panel w-full p-4 text-left transition hover:border-ink/15"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <span className={statusPill(incident.status)}>{humanizeSlug(incident.status)}</span>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/45">
                  {incident.trigger_types.map(humanizeSlug).join(", ")}
                </p>
              </div>
              <p className="mt-3 text-base font-semibold">
                {compact
                  ? incident.worker_name || incident.worker_id
                  : incident.claim_count > 1
                    ? `${incident.claim_count} linked claims`
                    : `Claim ${incident.claims[0].id.slice(0, 8)}`}
              </p>
              <p className="mt-1 text-sm text-ink/60">
                {formatDateTime(incident.created_at)}
                {incident.claim_count > 1 ? " · grouped into one disruption incident" : ""}
              </p>
              <p className="mt-2 text-sm text-ink/55">{reasoningLine(incident.status)}</p>
            </div>
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <p className="text-ink/45">Payout</p>
                <p className="font-semibold">
                  {formatCurrency(incident.total_final_payout || incident.total_calculated_payout)}
                </p>
              </div>
              <div>
                <p className="text-ink/45">Final score</p>
                <p className="font-semibold">{formatScore(incident.avg_final_score)}</p>
              </div>
              <div>
                <p className="text-ink/45">Fraud score</p>
                <p className="font-semibold">{formatScore(incident.max_fraud_score)}</p>
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
