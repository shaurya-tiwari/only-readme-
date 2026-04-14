import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, PlayCircle, Radar, RotateCcw, ShieldAlert, Wallet } from "lucide-react";

import { claimsApi } from "../api/claims";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import { triggersApi } from "../api/triggers";
import CausalityFlow from "../components/CausalityFlow";
import ScenarioCard from "../components/ScenarioCard";
import { SCENARIOS } from "../utils/constants";
import { formatCurrency, formatDateTime, formatPercent, humanizeSlug } from "../utils/formatters";

function buildActivityLog(latestResult, city) {
  if (!latestResult) {
    return [
      `Monitoring ${humanizeSlug(city)} for the next pinned demo run.`,
      "No deterministic demo story has been executed in this session yet.",
      "Use one of the four fixed demo stories to run a repeatable claim flow.",
    ];
  }

  const zone = latestResult.details?.[0];
  const fired = zone?.triggers_fired?.length ? zone.triggers_fired.map(humanizeSlug).join(", ") : "No triggers crossed";
  return [
    `SYS: Demo story executed for ${humanizeSlug(latestResult.city || city)}.`,
    latestResult.worker
      ? `WRK: ${latestResult.worker.name} loaded in ${humanizeSlug(latestResult.zone || city)}.`
      : "WRK: Fixed demo worker loaded.",
    `TRG: Triggers observed -> ${fired}.`,
    `LOG: ${latestResult.events_created} incident created, ${latestResult.events_extended} extended.`,
    `EXE: ${latestResult.claims_generated} claims processed, ${latestResult.claims_approved} approved, ${latestResult.claims_delayed} delayed, ${latestResult.claims_rejected} rejected.`,
    `PAY: Total payout impact ${formatCurrency(latestResult.total_payout || 0)}.`,
  ];
}

function parseActivityLine(line) {
  const [prefix, ...rest] = line.split(": ");
  if (!rest.length) {
    return { prefix: "LOG", message: line };
  }
  return { prefix, message: rest.join(": ") };
}

const causalitySteps = [
  { icon: Radar, label: "Signal ingest", text: "Threshold cross" },
  { icon: ShieldAlert, label: "Validation", text: "Incident created" },
  { icon: PlayCircle, label: "Processing", text: "Claims verified" },
  { icon: Wallet, label: "Settlement", text: "Payout issued" },
];

export default function DemoRunner() {
  const [selectedCity, setSelectedCity] = useState("delhi");
  const [runningScenario, setRunningScenario] = useState("");
  const [locations, setLocations] = useState({ cities: [], zones: [] });
  const [results, setResults] = useState({});
  const [claimStats, setClaimStats] = useState(null);
  const [payoutStats, setPayoutStats] = useState(null);
  const [status, setStatus] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [snapshotsLoading, setSnapshotsLoading] = useState(true);

  useEffect(() => {
    document.title = "Demo Runner | RideShield";
  }, []);

  const loadLocationConfig = useCallback(async () => {
    try {
      const response = await locationsApi.cities();
      setLocations((current) => ({ ...current, cities: response.data || [] }));
    } catch {
      // cities list is non-critical for demo runner
    }
    setSelectedCity("delhi");
  }, []);

  const refresh = useCallback(async () => {
    const [claimStatsRes, payoutStatsRes, diagnosticsRes] = await Promise.allSettled([
      claimsApi.stats({ days: 30 }),
      payoutsApi.stats({ days: 30 }),
      healthApi.getDiagnostics(),
    ]);
    if (claimStatsRes.status === "fulfilled") setClaimStats(claimStatsRes.value.data);
    if (payoutStatsRes.status === "fulfilled") setPayoutStats(payoutStatsRes.value.data);
    if (diagnosticsRes.status === "fulfilled") setDiagnostics(diagnosticsRes.value.data);
  }, []);

  const refreshSnapshots = useCallback(async () => {
    setSnapshotsLoading(true);
    try {
      const statusRes = await triggersApi.status({ city: "delhi" });
      setStatus(statusRes.data);
    } catch {
      // snapshots are non-critical — page remains usable
    } finally {
      setSnapshotsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh().catch(() => {});
  }, [refresh]);

  useEffect(() => {
    void refreshSnapshots().catch(() => {});
  }, [refreshSnapshots]);

  useEffect(() => {
    loadLocationConfig();
  }, [loadLocationConfig]);

  async function handleRun(scenarioId) {
    setRunningScenario(scenarioId);
    try {
      const response = await triggersApi.demoScenario(scenarioId);
      setResults((current) => ({ ...current, [scenarioId]: response.data }));
      await refresh();
      void refreshSnapshots().catch(() => {});
    } finally {
      setRunningScenario("");
    }
  }

  async function handleReset() {
    await triggersApi.reset();
    setResults({});
    await refresh();
    void refreshSnapshots().catch(() => {});
  }

  const latestResult = Object.values(results).at(-1) || null;
  const latestScenarioEntry = Object.entries(results).at(-1);
  const latestScenario = latestScenarioEntry ? SCENARIOS.find((item) => item.id === latestScenarioEntry[0]) : null;
  const snapshotSummary = useMemo(() => (status?.snapshots || []).slice(0, 4), [status]);
  const scheduler = diagnostics?.scheduler;
  const activityLog = buildActivityLog(latestResult, selectedCity);
  const cityLabel = locations.cities.find((city) => city.slug === selectedCity)?.display_name || humanizeSlug(selectedCity);

  return (
    <div className="space-y-8">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <p className="eyebrow">Demo runner</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-primary">Deterministic Demo Runner</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-on-surface-variant">
            Run four fixed RideShield stories with pinned worker profiles, pinned Delhi zones, and repeatable claim
            outcomes. This keeps the demo stable instead of depending on live variance.
          </p>
        </div>
        <div className="hidden items-center gap-2 rounded-[18px] bg-surface-container-low px-4 py-3 text-xs font-bold uppercase tracking-[0.24em] text-on-surface-variant lg:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          Demo locked
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <section className="space-y-6">
          <div className="decision-panel p-6">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="eyebrow">Demo controls</p>
                <h2 className="mt-2 text-2xl font-bold text-primary">Run repeatable product stories</h2>
              </div>
              <div className="flex flex-wrap items-center gap-3 rounded-[22px] bg-surface-container-low px-3 py-3">
                <div className="flex min-w-44 items-center rounded-full bg-surface-container-lowest px-4 py-2 text-sm font-semibold text-primary">
                  {cityLabel} fixed
                </div>
                <button
                  type="button"
                  className="button-secondary !rounded-full !border !border-outline-variant/50 !bg-surface-container-low !px-5 !py-2"
                  onClick={handleReset}
                >
                  <RotateCcw size={16} />
                  Reset demo state
                </button>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              {SCENARIOS.filter((s) => s.id !== 'gps_spoofing_attack').map((scenario) => (
                <div key={scenario.id} className="h-full">
                  <ScenarioCard
                    scenario={scenario}
                    running={runningScenario === scenario.id}
                    result={results[scenario.id]}
                    thresholds={status?.thresholds}
                    onRun={handleRun}
                  />
                </div>
              ))}
            </div>
            {SCENARIOS.filter((s) => s.id === 'gps_spoofing_attack').length > 0 && (
              <>
                <div className="flex items-center gap-3 pt-4">
                  <div className="h-px flex-1 bg-outline-variant/30" />
                  <span className="text-xs font-bold uppercase tracking-[0.24em] text-on-surface-variant">Adversarial tests</span>
                  <div className="h-px flex-1 bg-outline-variant/30" />
                </div>
                <div className="grid gap-5 md:grid-cols-2">
                  {SCENARIOS.filter((s) => s.id === 'gps_spoofing_attack').map((scenario) => (
                    <div key={scenario.id} className="h-full">
                      <ScenarioCard
                        scenario={scenario}
                        running={runningScenario === scenario.id}
                        result={results[scenario.id]}
                        thresholds={status?.thresholds}
                        onRun={handleRun}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          <div>
            <div className="mb-4 flex items-center gap-3 px-1">
              <Activity size={18} className="text-primary" />
              <h3 className="text-xl font-bold text-primary">Automation Logic: Product Flow</h3>
            </div>
            <CausalityFlow steps={causalitySteps} />
          </div>
        </section>

        <aside className="space-y-4">
          <div className={`decision-panel p-6 ${latestResult ? "scale-pop" : ""}`}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-primary">Results summary</h3>
              <span className="rounded-full bg-surface-container-low px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">
                {latestScenario ? latestScenario.title : "Awaiting run"}
              </span>
            </div>
            <div className="mt-6 space-y-4">
              {[
                { label: "Approved", value: latestResult?.claims_approved ?? 0 },
                { label: "Delayed", value: latestResult?.claims_delayed ?? 0 },
                { label: "Rejected", value: latestResult?.claims_rejected ?? 0 },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-sm text-on-surface-variant">{item.label}</span>
                  <span className="text-lg font-bold text-primary">{item.value}</span>
                </div>
              ))}
              <div className="border-t border-primary/10 pt-4">
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">Total payout</p>
                    <p className="mt-2 text-3xl font-bold text-primary">{formatCurrency(latestResult?.total_payout || 0)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">City</p>
                    <p className="mt-2 text-lg font-bold text-primary">{humanizeSlug(latestResult?.city || selectedCity)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="context-panel p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-[0.22em] text-primary">Live Activity Log</h3>
              <span className="text-[11px] font-mono text-on-surface-variant">Pinned flows</span>
            </div>
            <div className="max-h-72 space-y-3 overflow-y-auto text-sm">
              {activityLog.map((line, index) => {
                const parsed = parseActivityLine(line);

                return (
                  <div
                    key={`${line}-${index}`}
                    className={`rounded-[18px] border px-4 py-3 ${
                      index === activityLog.length - 1
                        ? "border-primary/25 bg-surface-container-high shadow-[inset_0_1px_0_rgba(105,248,233,0.08)]"
                        : "border-outline-variant/35 bg-surface-container-low/90"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="shrink-0 font-mono text-[11px] text-on-surface-variant">
                        {new Date(Date.now() - (activityLog.length - 1 - index) * 3000).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                      <div className="min-w-0">
                        <span className="inline-flex rounded-full bg-surface-container-highest px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-primary">
                          {parsed.prefix}
                        </span>
                        <p className="mt-2 font-mono leading-6 text-on-surface">{parsed.message}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="context-panel p-5">
            <p className="eyebrow">Engine status</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-[22px] border border-primary/5 p-5 panel-quiet">
                <p className="text-sm text-on-surface-variant">Claims in window</p>
                <p className="mt-3 text-3xl font-bold text-primary">{claimStats?.total_claims ?? 0}</p>
                <p className="mt-2 text-xs font-medium text-on-surface-variant">
                  Approval rate {formatPercent(claimStats?.approval_rate)}
                </p>
              </div>
              <div className="rounded-[22px] border border-primary/5 p-5 panel-quiet">
                <p className="text-sm text-on-surface-variant">Payout volume</p>
                <p className="mt-3 text-3xl font-bold text-primary">{formatCurrency(payoutStats?.total_amount)}</p>
                <p className="mt-2 text-xs font-medium text-on-surface-variant">{payoutStats?.total_payouts ?? 0} transfers</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3 rounded-[18px] border border-primary/8 bg-surface-container-low/80 px-4 py-3">
              <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-500" />
              <p className="text-sm text-on-surface-variant">
                Scheduler: every {scheduler?.interval_seconds || "--"}s · next {scheduler?.next_scheduled_at ? formatDateTime(scheduler.next_scheduled_at) : "--"}
              </p>
            </div>
          </div>

          <div className="context-panel p-5">
            <p className="eyebrow">Current signal snapshots</p>
            <div className="mt-4 space-y-3">
              {snapshotsLoading ? (
                <p className="text-sm text-on-surface-variant">Loading signal snapshots...</p>
              ) : snapshotSummary.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No snapshot data available.</p>
              ) : snapshotSummary.map((snapshot) => (
                <div key={snapshot.zone} className="rounded-[22px] p-4 panel-quiet">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-primary">{humanizeSlug(snapshot.zone)}</p>
                    <span
                      className={
                        snapshot.triggers_active.length
                          ? "pill-neutral"
                          : "inline-flex items-center rounded-full border border-tertiary/25 bg-tertiary-container/45 px-3 py-1 text-xs font-semibold text-tertiary-fixed"
                      }
                    >
                      {snapshot.triggers_active.length} triggers
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {snapshot.triggers_active.length
                      ? snapshot.triggers_active.map(humanizeSlug).join(", ")
                      : "No active threshold breaches"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
