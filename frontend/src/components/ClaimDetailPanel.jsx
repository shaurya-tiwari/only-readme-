import { formatCurrency, formatDateTime, formatScore, humanizeSlug, statusPill } from "../utils/formatters";

function renderTriggerList(triggers = []) {
  if (!triggers.length) {
    return "None";
  }
  return triggers.map(humanizeSlug).join(", ");
}

export default function ClaimDetailPanel({ claim }) {
  if (!claim) {
    return (
      <div className="panel p-6">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Claim detail</p>
          <h3 className="mt-1 text-2xl font-bold">Select an incident</h3>
        </div>
        <p className="text-sm text-ink/60">
          Pick a claim incident from the worker feed to inspect why it was approved, delayed, or rejected.
        </p>
      </div>
    );
  }

  const breakdown = claim.decision_breakdown || {};
  const inputs = breakdown.inputs || {};
  const components = breakdown.breakdown || {};
  const incidentTriggers = inputs.incident_triggers || claim.decision_breakdown?.incident_triggers || [claim.trigger_type];
  const coveredTriggers = inputs.covered_triggers || claim.decision_breakdown?.covered_triggers || [];

  return (
    <div className="panel p-6">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Claim detail</p>
        <div className="mt-2 flex items-center gap-3">
          <span className={statusPill(claim.status)}>{humanizeSlug(claim.status)}</span>
          <h3 className="text-2xl font-bold">{renderTriggerList(incidentTriggers)}</h3>
        </div>
        <p className="mt-2 text-sm text-ink/60">{formatDateTime(claim.created_at)}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/50">Decision explanation</p>
          <p className="mt-2 text-sm text-ink/75">{breakdown.explanation || claim.rejection_reason || "No explanation available."}</p>
        </div>
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/50">Payout impact</p>
          <p className="mt-2 text-lg font-semibold">{formatCurrency(claim.final_payout || claim.calculated_payout)}</p>
          <p className="mt-2 text-sm text-ink/65">Hours affected: {claim.disruption_hours ?? "--"} · Peak multiplier: {claim.peak_multiplier ?? "--"}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-sm text-ink/45">Final score</p>
          <p className="font-semibold">{formatScore(claim.final_score)}</p>
        </div>
        <div>
          <p className="text-sm text-ink/45">Fraud score</p>
          <p className="font-semibold">{formatScore(claim.fraud_score)}</p>
        </div>
        <div>
          <p className="text-sm text-ink/45">Event confidence</p>
          <p className="font-semibold">{formatScore(claim.event_confidence)}</p>
        </div>
        <div>
          <p className="text-sm text-ink/45">Trust score</p>
          <p className="font-semibold">{formatScore(claim.trust_score)}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/50">Incident triggers</p>
          <p className="mt-2 text-sm text-ink/75">{renderTriggerList(incidentTriggers)}</p>
          <p className="mt-3 text-sm text-ink/50">Covered by policy</p>
          <p className="mt-2 text-sm text-ink/75">{renderTriggerList(coveredTriggers)}</p>
        </div>
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/50">Score breakdown</p>
          <div className="mt-2 grid gap-2 text-sm text-ink/75">
            <p>Disruption component: {formatScore(components.disruption_component)}</p>
            <p>Confidence component: {formatScore(components.confidence_component)}</p>
            <p>Fraud component: {formatScore(components.fraud_component)}</p>
            <p>Trust component: {formatScore(components.trust_component)}</p>
            <p>Flag penalty: {formatScore(components.flag_penalty)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
