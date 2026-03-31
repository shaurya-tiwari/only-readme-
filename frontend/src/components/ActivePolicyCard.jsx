import { Clock3, ShieldCheck } from "lucide-react";

import { formatCurrency, formatDateTime, humanizeSlug, statusPill } from "../utils/formatters";

export default function ActivePolicyCard({ policy, pendingPolicy }) {
  if (!policy && !pendingPolicy) {
    return (
      <div className="panel p-6">
        <p className="eyebrow">Coverage</p>
        <h3 className="mt-2 text-xl font-bold text-[#173126]">No active policy</h3>
        <p className="mt-2 text-sm leading-6 text-ink/60">Register or buy a plan to activate protection.</p>
      </div>
    );
  }

  const data = policy || pendingPolicy;

  return (
    <div className="panel p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Coverage</p>
          <h3 className="mt-2 text-2xl font-bold text-[#173126]">{data.display_name || humanizeSlug(data.plan_name)}</h3>
        </div>
        <span className={statusPill(data.status || (policy ? "active" : "pending"))}>{policy ? "Active" : "Pending"}</span>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-ink/55">Premium</p>
          <p className="mt-2 text-xl font-bold text-[#173126]">{policy ? formatCurrency(data.weekly_premium) : "--"}</p>
        </div>
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-ink/55">Coverage cap</p>
          <p className="mt-2 text-xl font-bold text-[#173126]">{policy ? formatCurrency(data.coverage_cap) : "--"}</p>
        </div>
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-ink/55">{policy ? "Expires" : "Activates"}</p>
          <p className="mt-2 text-sm font-semibold text-[#173126]">{formatDateTime(policy ? data.expires_at : data.activates_at)}</p>
        </div>
      </div>

      <div className="mt-5 flex items-start gap-3 rounded-[24px] bg-[linear-gradient(135deg,#003527_0%,#064e3b_100%)] px-4 py-4 text-white">
        {policy ? <ShieldCheck size={18} className="mt-0.5" /> : <Clock3 size={18} className="mt-0.5" />}
        <div className="text-sm leading-6">
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
