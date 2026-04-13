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
  const worker = result?.worker;
  const summaryRows = result
    ? [
        { label: "Incidents", value: result.events_created },
        { label: "Claims", value: result.claims_generated },
        { label: "Approved", value: result.claims_approved },
        { label: "Payout", value: formatCurrency(result.total_payout || 0) },
      ]
    : [];
  const detailRows = result
    ? [
        {
          label: "Incident step",
          value:
            result.events_created > 0
              ? "Incident created"
              : result.events_extended > 0
                ? "Incident extended"
                : "No incident change",
        },
        { label: "Worker impact", value: `${result.claims_generated} claims processed` },
        {
          label: "Decision mix",
          value: `${result.claims_approved} approved | ${result.claims_delayed} delayed | ${result.claims_rejected} rejected`,
        },
      ]
    : [];

  return (
    <div className="group panel h-full min-h-[252px] overflow-hidden p-6 card-hover transition-smooth">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Scenario</p>
          <h3 className="mt-2 text-2xl font-bold text-primary">{scenario.title}</h3>
        </div>
        <button type="button" onClick={() => onRun(scenario.id)} disabled={running} className="button-primary !rounded-xl !px-4 !py-2 text-sm transition-smooth group-hover:brightness-110">
          <Play size={16} />
          {running ? "Running" : "Run"}
        </button>
      </div>

      <p className="text-sm leading-6 text-on-surface-variant">{scenario.summary}</p>
      <p className="mt-3 text-sm font-medium text-on-surface-variant">{scenario.outcome}</p>
      <p className="mt-3 text-xs uppercase tracking-[0.18em] text-on-surface-variant">
        {humanizeSlug(scenario.city)} / {humanizeSlug(scenario.zone)} | {scenario.setup}
      </p>

      {result ? (
        <div className="mt-5 space-y-4 rounded-[24px] border border-primary/10 bg-surface-container-lowest/95 p-5 shadow-[inset_0_1px_0_rgba(105,248,233,0.05)]">
          {worker ? (
            <div className="rounded-[22px] border border-primary/8 bg-surface-container-high/90 p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">Demo worker</p>
              <p className="mt-3 font-semibold leading-6 text-on-surface">
                {worker.name} in {humanizeSlug(result.zone || scenario.zone)}
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">{result.expected_path || scenario.outcome}</p>
            </div>
          ) : null}

          <div className="space-y-3">
            {summaryRows.map((row) => (
              <div key={row.label} className="flex items-center justify-between gap-4 rounded-[20px] border border-primary/8 bg-surface-container-high/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">{row.label}</p>
                <p className="text-2xl font-extrabold tracking-tight text-primary sm:text-3xl">{row.value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-[22px] border border-primary/8 bg-surface-container-high/90 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">Cause and effect</p>
            <div className="mt-4 space-y-3 text-sm leading-7 text-on-surface">
              <p>
                RideShield runs a fixed worker story, applies the matching disruption scenario, and then checks the live
                trigger thresholds before creating or extending an incident.
              </p>
              {firedTriggers.length ? (
                <p className="font-semibold text-primary">Triggers crossed: {firedTriggers.map(humanizeSlug).join(", ")}</p>
              ) : (
                <p className="font-semibold text-primary">No trigger crossed the configured threshold on this run.</p>
              )}
              {signals.rain !== undefined ? <p className="text-on-surface-variant">{explainSignal("Rain", signals.rain, thresholds?.rain, " mm/hr")}</p> : null}
              {signals.traffic !== undefined ? <p className="text-on-surface-variant">{explainSignal("Traffic", signals.traffic, thresholds?.traffic)}</p> : null}
              {signals.platform_outage !== undefined ? (
                <p className="text-on-surface-variant">{explainSignal("Platform drop", signals.platform_outage, thresholds?.platform_outage)}</p>
              ) : null}
              {signals.aqi !== undefined ? <p className="text-on-surface-variant">{explainSignal("AQI", signals.aqi, thresholds?.aqi)}</p> : null}
              {signals.heat !== undefined ? <p className="text-on-surface-variant">{explainSignal("Heat", signals.heat, thresholds?.heat, " C")}</p> : null}
            </div>
          </div>

          <div className="space-y-3 text-sm">
            {detailRows.map((row) => (
              <div key={row.label} className="rounded-[22px] border border-primary/8 bg-surface-container-high/80 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">{row.label}</p>
                <p className="mt-3 font-semibold leading-6 text-on-surface">{row.value}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
