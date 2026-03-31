import { AlertTriangle } from "lucide-react";

import { formatScore, humanizeSlug, riskLabel } from "../utils/formatters";

export default function RiskGauge({ score, breakdown }) {
  const meta = riskLabel(score);
  const items = Object.entries(breakdown || {}).filter(([key]) => typeof breakdown[key] === "number");

  return (
    <div className="panel overflow-hidden p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Risk model</p>
          <h3 className="mt-1 text-2xl font-bold">Current risk score</h3>
        </div>
        <div className={`rounded-2xl px-4 py-3 ${meta.tone} bg-current/10 text-right`}>
          <p className="text-3xl font-bold">{formatScore(score)}</p>
          <p className="text-sm">{meta.label}</p>
        </div>
      </div>
      {items.length ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {items.map(([key, value]) => (
            <div key={key} className="rounded-2xl bg-black/[0.03] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">{humanizeSlug(key)}</p>
              <p className="mt-2 text-xl font-semibold">{formatScore(value)}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl bg-black/[0.03] p-4 text-sm text-ink/65">
          <AlertTriangle className="mb-2" size={18} />
          Detailed factor breakdown will appear after registration.
        </div>
      )}
    </div>
  );
}
