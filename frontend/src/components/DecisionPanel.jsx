import { decisionConfidenceCopy, humanizeSlug, statusPill } from "../utils/formatters";
import { workerClaimNarrative } from "../utils/decisionNarrative";

/**
 * Worker-facing decision panel — shows the most relevant claim context,
 * the confidence score, and a plain-English explanation of the decision.
 *
 * Extracted from Dashboard.jsx to make it independently importable and testable.
 *
 * @param {{ claim: object|null, narrative: string }} props
 */
export default function DecisionPanel({ claim, narrative }) {
  const decisionState = claim?.status || "idle";
  const confidenceLabel = decisionConfidenceCopy(claim?.decision_confidence_band, claim?.status);

  let heading = "No active claim needs attention right now.";
  let reason =
    "RideShield is monitoring your zone and will create a claim automatically if a covered incident is verified.";

  if (claim?.status === "delayed") {
    heading = "Your latest claim is waiting for a manual check.";
    reason = workerClaimNarrative(claim);
  } else if (claim?.status === "approved") {
    heading = "Your latest decision is already approved.";
    reason = workerClaimNarrative(claim);
  } else if (claim?.status === "rejected") {
    heading = "The latest claim was rejected.";
    reason = workerClaimNarrative(claim);
  }

  return (
    <div className="decision-panel card-primary p-6 lg:sticky lg:top-24">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Decision panel</p>
          <h2 className="mt-3 text-2xl font-bold leading-tight text-primary">{heading}</h2>
        </div>
        <span className={statusPill(decisionState)}>{humanizeSlug(decisionState)}</span>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <span className="pill bg-primary/10 text-primary">{confidenceLabel}</span>
        {claim?.id ? <span className="pill bg-white text-on-surface-variant">Claim {claim.id.slice(0, 6)}</span> : null}
      </div>

      <div className="mt-5 panel-quiet rounded-[24px] p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">Why this matters now</p>
        <p className="mt-3 text-sm leading-6 text-on-surface">{reason}</p>
      </div>

      <div className="mt-5 panel-quiet rounded-[24px] p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">Protection narrative</p>
        <p className="mt-3 text-sm leading-6 text-on-surface">{narrative}</p>
      </div>
    </div>
  );
}
