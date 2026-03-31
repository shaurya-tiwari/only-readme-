import { Clock3, ShieldCheck } from "lucide-react";

import { formatCurrency, formatDateTime, humanizeSlug, statusPill } from "../utils/formatters";

export default function ActivePolicyCard({ policy, pendingPolicy }) {
  if (!policy && !pendingPolicy) {
    return (
      <div className="panel p-6">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-ink/45">Coverage</p>
        <h3 className="mt-2 text-xl font-bold">No active policy</h3>
        <p className="mt-2 text-sm text-ink/60">Register or buy a plan to activate protection.</p>
      </div>
    );
  }

  const data = policy || pendingPolicy;

  return (
    <div className="panel p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Coverage</p>
          <h3 className="mt-1 text-2xl font-bold">{data.display_name || humanizeSlug(data.plan_name)}</h3>
        </div>
        <span className={statusPill(data.status || (policy ? "active" : "pending"))}>
          {policy ? "Active" : "Pending"}
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/55">Premium</p>
          <p className="mt-2 text-xl font-bold">{policy ? formatCurrency(data.weekly_premium) : "--"}</p>
        </div>
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/55">Coverage cap</p>
          <p className="mt-2 text-xl font-bold">{policy ? formatCurrency(data.coverage_cap) : "--"}</p>
        </div>
        <div className="rounded-2xl bg-black/[0.03] p-4">
          <p className="text-sm text-ink/55">{policy ? "Expires" : "Activates"}</p>
          <p className="mt-2 text-sm font-semibold">{formatDateTime(policy ? data.expires_at : data.activates_at)}</p>
        </div>
      </div>
      <div className="mt-5 flex items-start gap-3 rounded-2xl bg-ink px-4 py-4 text-white">
        {policy ? <ShieldCheck size={18} className="mt-0.5" /> : <Clock3 size={18} className="mt-0.5" />}
        <div className="text-sm">
          {policy ? (
            <p>Triggers covered: {(data.triggers_covered || []).map(humanizeSlug).join(", ")}</p>
          ) : (
            <p>Activation in {Math.ceil(data.hours_until_activation || 0)} hours unless demo force-activation is used.</p>
          )}
        </div>
      </div>
    </div>
  );
}
