import { formatCurrency, humanizeSlug, statusPill } from "../utils/formatters";

export default function ClaimStatus({ claim }) {
  if (!claim) {
    return null;
  }

  const triggers =
    claim.decision_breakdown?.incident_triggers ||
    claim.decision_breakdown?.inputs?.incident_triggers ||
    [claim.trigger_type];

  return (
    <div className="rounded-2xl bg-black/[0.03] p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={statusPill(claim.status)}>{humanizeSlug(claim.status)}</span>
        <p className="font-semibold">{triggers.map(humanizeSlug).join(", ")}</p>
      </div>
      <p className="mt-2 text-sm text-ink/60">
        {claim.status === "approved"
          ? `System payout approved for ${formatCurrency(claim.final_payout || claim.calculated_payout)}.`
          : claim.status === "delayed"
            ? "This incident needs manual review before payout can be released."
            : "This incident was rejected after signal validation and fraud checks."}
      </p>
    </div>
  );
}
