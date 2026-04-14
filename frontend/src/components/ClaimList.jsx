import { groupClaimsByIncident } from "../utils/claimGroups";
import { formatCurrency, formatDateTime, formatScore, humanizeSlug, statusPill } from "../utils/formatters";

function reasoningLine(status) {
  if (status === "approved") {
    return "Approved because the disruption evidence stayed strong and the account checks stayed clear.";
  }
  if (status === "delayed") {
    return "Delayed because the incident looks real but the system wants an admin decision before payout.";
  }
  return "Rejected because the disruption and account checks did not support a safe payout.";
}

export default function ClaimList({ claims = [], onSelect, compact = false }) {
  if (!claims.length) {
    return <p className="text-sm text-on-surface-variant">No claims found for this view.</p>;
  }

  const incidents = groupClaimsByIncident(claims, { bucketMinutes: 90 });

  return (
    <div className="overflow-hidden rounded-[24px] border border-outline-variant/60">
      <div className="hidden grid-cols-[1.4fr_1fr_1fr_0.9fr_0.9fr_0.8fr] gap-3 bg-surface-container-low px-4 py-4 text-[11px] font-bold uppercase tracking-[0.22em] text-on-surface-variant md:grid">
        <span>Incident</span>
        <span>Zone</span>
        <span>Triggers</span>
        <span>Status</span>
        <span>Amount</span>
        <span>Score</span>
      </div>
      <div className="divide-y divide-outline-variant/40">
        {incidents.map((incident) => (
          <button
            key={incident.id}
            type="button"
            onClick={() => onSelect?.(incident.claims[0])}
            className="grid w-full gap-3 bg-surface-container-lowest px-4 py-4 text-left transition hover:bg-surface md:grid-cols-[1.4fr_1fr_1fr_0.9fr_0.9fr_0.8fr]"
          >
            <div>
              <p className="text-base font-semibold text-primary">
                {compact
                  ? incident.worker_name || incident.worker_id
                  : incident.claim_count > 1
                    ? `${incident.claim_count} linked claims`
                    : `Claim ${incident.claims[0].id.slice(0, 8)}`}
              </p>
              <p className="mt-1 text-sm text-on-surface-variant">
                {formatDateTime(incident.created_at)}
                {incident.claim_count > 1 ? " - grouped into one disruption incident" : ""}
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant md:hidden">{reasoningLine(incident.status)}</p>
            </div>
            <div className="text-sm text-on-surface-variant">{humanizeSlug(incident.zone || "zone")}</div>
            <div className="text-sm text-on-surface-variant">{incident.trigger_types.map(humanizeSlug).join(", ")}</div>
            <div><span className={statusPill(incident.status)}>{humanizeSlug(incident.status)}</span></div>
            <div className="text-sm font-semibold text-primary">
              {formatCurrency(incident.total_final_payout || incident.total_calculated_payout)}
            </div>
            <div className="text-sm font-semibold text-primary">{formatScore(incident.avg_final_score)}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
