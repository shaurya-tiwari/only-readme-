import { Play } from "lucide-react";

import { formatCurrency, humanizeSlug } from "../utils/formatters";

function explainSignal(label, value, threshold, unit = "") {
  const numericValue = typeof value === "number" ? value : Number(value || 0);
  const numericThreshold = typeof threshold === "number" ? threshold : Number(threshold || 0);
  return `${label}: ${numericValue}${unit} (threshold ${numericThreshold}${unit})`;
}

export default function ScenarioCard({ scenario, running, result, thresholds, onRun }) {
  const zoneResult = result?.details?.[0];
  const signals = zoneResult?.signals || {};
  const firedTriggers = zoneResult?.triggers_fired || [];

  return (
    <div className="panel p-6">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Scenario</p>
          <h3 className="mt-1 text-2xl font-bold">{scenario.title}</h3>
        </div>
        <button type="button" onClick={() => onRun(scenario.id)} disabled={running} className="button-primary !rounded-xl !px-4 !py-2 text-sm">
          <Play size={16} />
          {running ? "Running" : "Run"}
        </button>
      </div>
      <p className="text-sm text-ink/65">{scenario.summary}</p>
      <p className="mt-3 text-sm font-medium text-ink/70">{scenario.outcome}</p>
      {result ? (
        <div className="mt-5 space-y-4 rounded-2xl bg-black/[0.03] p-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Events</p>
              <p className="mt-2 text-xl font-bold">{result.events_created}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Claims</p>
              <p className="mt-2 text-xl font-bold">{result.claims_generated}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Approved</p>
              <p className="mt-2 text-xl font-bold">{result.claims_approved}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Payout</p>
              <p className="mt-2 text-xl font-bold">{formatCurrency(result.total_payout || 0)}</p>
            </div>
          </div>

          <div className="rounded-2xl bg-white/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/45">Cause and effect</p>
            <div className="mt-3 space-y-2 text-sm text-ink/70">
              <p>
                Scenario changes the simulator inputs for the selected zone. The trigger engine then checks real thresholds and decides whether an incident should be created or extended.
              </p>
              {firedTriggers.length ? (
                <p className="font-medium text-ink">
                  Triggers crossed: {firedTriggers.map(humanizeSlug).join(", ")}
                </p>
              ) : (
                <p className="font-medium text-ink">No trigger crossed the configured threshold on this run.</p>
              )}
              {signals.rain !== undefined ? (
                <p>{explainSignal("Rain", signals.rain, thresholds?.rain, " mm/hr")}</p>
              ) : null}
              {signals.traffic !== undefined ? (
                <p>{explainSignal("Traffic", signals.traffic, thresholds?.traffic)}</p>
              ) : null}
              {signals.platform_outage !== undefined ? (
                <p>{explainSignal("Platform drop", signals.platform_outage, thresholds?.platform_outage)}</p>
              ) : null}
              {signals.aqi !== undefined ? (
                <p>{explainSignal("AQI", signals.aqi, thresholds?.aqi)}</p>
              ) : null}
              {signals.heat !== undefined ? (
                <p>{explainSignal("Heat", signals.heat, thresholds?.heat, " C")}</p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Incident step</p>
              <p className="mt-2 font-semibold">
                {result.events_created > 0 ? "Incident created" : result.events_extended > 0 ? "Incident extended" : "No incident change"}
              </p>
            </div>
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Worker impact</p>
              <p className="mt-2 font-semibold">{result.claims_generated} claims processed</p>
            </div>
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/45">Decision mix</p>
              <p className="mt-2 font-semibold">
                {result.claims_approved} approved · {result.claims_delayed} delayed · {result.claims_rejected} rejected
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
