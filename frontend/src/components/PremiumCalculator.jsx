import { formatCurrency, formatScore } from "../utils/formatters";

export default function PremiumCalculator({ selectedPlan }) {
  if (!selectedPlan) {
    return (
      <div className="panel p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Premium model</p>
        <h3 className="mt-1 text-2xl font-bold">Weekly price formula</h3>
        <p className="mt-3 text-sm text-ink/60">
          Premiums follow the README formula: base price x plan factor x worker risk score, with guardrails on the final weekly charge.
        </p>
      </div>
    );
  }

  const base = Number(selectedPlan.base_price || 0);
  const factor = Number(selectedPlan.plan_factor || 0);
  const risk = Number(selectedPlan.risk_score || 0);
  const raw = base * factor * risk;

  return (
    <div className="panel p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Premium model</p>
      <h3 className="mt-1 text-2xl font-bold">{selectedPlan.plan_display_name}</h3>
      <p className="mt-3 text-sm text-ink/60">
        Base {formatCurrency(base)} x factor {factor.toFixed(1)} x risk {formatScore(risk)} = {formatCurrency(raw)} before plan safeguards.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/45">Final weekly premium</p>
          <p className="mt-2 text-2xl font-bold">{formatCurrency(selectedPlan.weekly_premium)}</p>
        </div>
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/45">Coverage cap</p>
          <p className="mt-2 text-2xl font-bold">{formatCurrency(selectedPlan.coverage_cap)}</p>
        </div>
      </div>
    </div>
  );
}
