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
    <div className="panel-quiet rounded-[24px] p-5">
      <div className="flex flex-wrap items-center gap-3">
        <span className={statusPill(claim.status)}>{humanizeSlug(claim.status)}</span>
        <p className="font-semibold text-[#173126]">{triggers.map(humanizeSlug).join(", ")}</p>
      </div>
      <h3 className="mt-4 text-lg font-bold text-primary">Why was this claim {humanizeSlug(claim.status)}?</h3>
      <p className="mt-3 text-sm leading-6 text-ink/60">
        {claim.status === "approved"
          ? `System payout approved for ${formatCurrency(claim.final_payout || claim.calculated_payout)}.`
          : claim.status === "delayed"
            ? "This incident needs manual review before payout can be released."
            : "This incident was rejected after signal validation and fraud checks."}
      </p>
      <p className="mt-3 text-sm leading-6 text-on-surface-variant">
        {claim.decision_breakdown?.explanation || "The claim outcome reflects disruption strength, trust context, and fraud risk."}
      </p>
    </div>
  );
}
