import clsx from "clsx";

import { formatCurrency, humanizeSlug } from "../utils/formatters";

export default function PlanCard({ plan, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(plan.plan_name)}
      className={clsx(
        "panel w-full p-5 text-left transition hover:-translate-y-0.5 hover:border-ink/15",
        selected ? "border-ink ring-2 ring-ink/10" : "border-black/5",
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">{humanizeSlug(plan.plan_name)}</p>
          <h3 className="mt-1 text-xl font-bold">{plan.display_name || humanizeSlug(plan.plan_name)}</h3>
        </div>
        {plan.is_recommended ? <span className="pill bg-gold/20 text-amber-800">Recommended</span> : null}
      </div>
      <p className="mb-4 text-sm text-ink/60">{plan.description}</p>
      <div className="mb-4 flex items-end gap-2">
        <p className="text-3xl font-bold">{formatCurrency(plan.weekly_premium)}</p>
        <p className="pb-1 text-sm text-ink/55">per week</p>
      </div>
      <div className="mb-4 rounded-2xl bg-black/[0.03] p-4 text-sm text-ink/70">
        <p>Coverage cap: {formatCurrency(plan.coverage_cap)}</p>
        <p className="mt-1">Triggers: {(plan.triggers_covered || []).map(humanizeSlug).join(", ")}</p>
      </div>
      <span className={clsx("text-sm font-semibold", selected ? "text-storm" : "text-ink/65")}>
        {selected ? "Selected" : "Choose plan"}
      </span>
    </button>
  );
}
