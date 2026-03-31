import { useEffect, useMemo, useState } from "react";
import { Activity, ChevronRight, PlayCircle, Radar, ShieldAlert, Wallet } from "lucide-react";

import ScenarioCard from "../components/ScenarioCard";
import { claimsApi } from "../api/claims";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import { policiesApi } from "../api/policies";
import { triggersApi } from "../api/triggers";
import { workersApi } from "../api/workers";
import { SCENARIOS } from "../utils/constants";
import { formatCurrency, formatDateTime, formatPercent, humanizeSlug } from "../utils/formatters";

function buildActivityLog(latestResult, city) {
  if (!latestResult) {
    return [
      `Monitoring ${humanizeSlug(city)} for threshold breaches.`,
      "No explicit scenario run yet in this session.",
      "Use a scenario card to force a visible cause-and-effect cycle.",
    ];
  }

  const zone = latestResult.details?.[0];
  const fired = zone?.triggers_fired?.length ? zone.triggers_fired.map(humanizeSlug).join(", ") : "No triggers crossed";
  return [
    `SYS: Scenario executed for ${humanizeSlug(city)}.`,
    `TRG: Triggers observed -> ${fired}.`,
    `LOG: ${latestResult.events_created} incident created, ${latestResult.events_extended} extended.`,
    `EXE: ${latestResult.claims_generated} claims processed, ${latestResult.claims_approved} approved, ${latestResult.claims_delayed} delayed, ${latestResult.claims_rejected} rejected.`,
    `PAY: Total payout impact ${formatCurrency(latestResult.total_payout || 0)}.`,
  ];
}

export default function DemoRunner() {
  const [selectedCity, setSelectedCity] = useState("delhi");
  const [runningScenario, setRunningScenario] = useState("");
  const [locations, setLocations] = useState({ cities: [], zones: [] });
  const [results, setResults] = useState({});
  const [claimStats, setClaimStats] = useState(null);
  const [payoutStats, setPayoutStats] = useState(null);
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [setupLoading, setSetupLoading] = useState(false);

  useEffect(() => {
    document.title = "Demo Runner | RideShield";
  }, []);

  useEffect(() => {
    refresh();
  }, [selectedCity]);

  useEffect(() => {
    setResults({});
  }, [selectedCity]);

  useEffect(() => {
    loadLocationConfig();
  }, []);

  async function loadLocationConfig() {
    const response = await locationsApi.config();
    const data = response.data || { cities: [], zones: [] };
    setLocations(data);
    if (data.cities?.length && !data.cities.some((city) => city.slug === selectedCity)) {
      setSelectedCity(data.cities[0].slug);
    }
  }

  async function refresh() {
    const [claimStatsRes, payoutStatsRes, statusRes, configRes] = await Promise.all([
      claimsApi.stats({ days: 30 }),
      payoutsApi.stats({ days: 30 }),
      triggersApi.status({ city: selectedCity }),
      healthApi.getConfig(),
    ]);
    setClaimStats(claimStatsRes.data);
    setPayoutStats(payoutStatsRes.data);
    setStatus(statusRes.data);
    setConfig(configRes.data);
  }

  async function handleRun(scenarioId) {
    setRunningScenario(scenarioId);
    try {
      const demoRunId = `${selectedCity}-${scenarioId}-${Date.now()}`;
      await triggersApi.scenario(scenarioId, { city: selectedCity });
      const response = await triggersApi.check({ city: selectedCity, scenario: scenarioId, demo_run_id: demoRunId });
      setResults((current) => ({ ...current, [scenarioId]: response.data }));
      await refresh();
    } finally {
      setRunningScenario("");
    }
  }

  async function handleReset() {
    await triggersApi.reset();
    setResults({});
    await refresh();
  }

  async function createDemoWorker() {
    setSetupLoading(true);
    try {
      const phone = `+91${String(Date.now()).slice(-10)}`;
      const zone = locations.zones.find((item) => item.city_slug === selectedCity)?.slug || "south_delhi";
      const worker = await workersApi.register({
        name: `${humanizeSlug(selectedCity)} Demo Rider`,
        phone,
        city: selectedCity,
        zone,
        platform: selectedCity === "bengaluru" || selectedCity === "chennai" ? "swiggy" : "zomato",
        self_reported_income: 900,
        working_hours: 9,
        consent_given: true,
      });
      await policiesApi.create({
        worker_id: worker.data.worker_id,
        plan_name: "smart_protect",
      });
      await policiesApi.forceActivate(worker.data.worker_id);
      await refresh();
    } finally {
      setSetupLoading(false);
    }
  }

  const latestResult = Object.values(results).at(-1) || null;
  const latestScenarioEntry = Object.entries(results).at(-1);
  const latestScenario = latestScenarioEntry ? SCENARIOS.find((item) => item.id === latestScenarioEntry[0]) : null;
  const snapshotSummary = useMemo(() => (status?.snapshots || []).slice(0, 4), [status]);
  const scheduler = config?.scheduler;
  const activityLog = buildActivityLog(latestResult, selectedCity);

  return (
    <div className="space-y-8">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <p className="eyebrow">Demo runner</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-[#173126]">Simulation Control Center</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-ink/65">
            Use real trigger APIs to force a visible RideShield cycle: signal threshold crossed, incident created, claims
            processed, payouts completed.
          </p>
        </div>
        <div className="hidden items-center gap-2 rounded-[18px] bg-[#f4f4ef] px-4 py-3 text-xs font-bold uppercase tracking-[0.24em] text-ink/55 lg:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          Engine live
        </div>
      </section>

      <div className="grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="space-y-6">
          <div className="panel p-6">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="eyebrow">Scenario controls</p>
                <h2 className="mt-2 text-2xl font-bold text-[#173126]">Run environment changes deliberately</h2>
              </div>
              <div className="flex flex-wrap gap-3">
                <select className="field min-w-44 !rounded-full !bg-[#f4f4ef] !py-2" value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
                  {locations.cities.map((city) => (
                    <option key={city.id} value={city.slug}>
                      {city.display_name}
                    </option>
                  ))}
                </select>
              <button type="button" className="button-secondary !rounded-full !py-2" onClick={createDemoWorker} disabled={setupLoading}>
                  {setupLoading ? "Creating..." : "Create demo worker"}
                </button>
                <button type="button" className="button-secondary !rounded-full !bg-[#eef3ef] !py-2" onClick={handleReset}>
                  Reset simulators
                </button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {SCENARIOS.map((scenario) => (
                <ScenarioCard
                  key={scenario.id}
                  scenario={scenario}
                  running={runningScenario === scenario.id}
                  result={results[scenario.id]}
                  thresholds={status?.thresholds}
                  onRun={handleRun}
                />
              ))}
            </div>
          </div>

          <div className="panel-quiet rounded-[28px] p-6">
            <div className="mb-6 flex items-center gap-3">
              <Activity size={18} className="text-[#173126]" />
              <h3 className="text-xl font-bold text-[#173126]">Automation Logic: Causality Flow</h3>
            </div>
            <div className="relative grid gap-4 md:grid-cols-4">
              <div className="absolute left-[12%] right-[12%] top-7 hidden h-0.5 bg-outline-variant md:block" />
              {[
                { icon: Radar, label: "Signal ingest", text: "Threshold cross" },
                { icon: ShieldAlert, label: "Validation", text: "Incident created" },
                { icon: PlayCircle, label: "Processing", text: "Claims verified" },
                { icon: Wallet, label: "Settlement", text: "Payout issued" },
              ].map(({ icon: Icon, label, text }, index) => (
                <div key={label} className="relative">
                  <div className="flex flex-col items-center text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-[#173126] shadow-[0_10px_25px_rgba(26,28,25,0.08)]">
                      <Icon size={20} />
                    </div>
                    <p className="mt-3 text-[11px] font-bold uppercase tracking-[0.24em] text-ink/45">{label}</p>
                    <p className="mt-1 text-sm font-semibold text-[#173126]">{text}</p>
                  </div>
                  {index < 3 ? <ChevronRight size={18} className="absolute right-[-18px] top-5 hidden text-ink/30 md:hidden" /> : null}
                </div>
              ))}
            </div>
            <p className="mt-6 text-sm leading-7 text-ink/65">
              The scenario button does not create claims directly. It changes the environment, then the actual RideShield
              engine applies thresholds, merges incidents, scores claims, and decides payouts.
            </p>
          </div>
        </section>

        <aside className="space-y-6">
          <div className="hero-glow rounded-[28px] p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold">Results Summary</h3>
              <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-white/75">
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
                  <span className="text-sm text-white/80">{item.label}</span>
                  <span className="text-lg font-bold">{item.value}</span>
                </div>
              ))}
              <div className="border-t border-white/10 pt-4">
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Total payout</p>
                    <p className="mt-2 text-3xl font-bold">{formatCurrency(latestResult?.total_payout || 0)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">City</p>
                    <p className="mt-2 text-lg font-bold">{humanizeSlug(selectedCity)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="panel p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-[0.22em] text-[#173126]">Live Activity Log</h3>
              <span className="text-[11px] font-mono text-ink/45">STREAM ACTIVE</span>
            </div>
            <div className="max-h-80 space-y-3 overflow-y-auto text-sm">
              {activityLog.map((line, index) => (
                <div key={`${line}-${index}`} className={`flex gap-3 rounded-[18px] border-l-2 px-3 py-3 ${index === activityLog.length - 1 ? "border-primary bg-white/60" : "border-transparent bg-surface-container-low"}`}>
                  <span className="shrink-0 font-mono text-[11px] text-ink/45">
                    {new Date(Date.now() - (activityLog.length - 1 - index) * 3000).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                  <p className="font-mono leading-6 text-ink/70">{line}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="panel p-6">
            <p className="eyebrow">Engine status</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="panel-quiet rounded-[22px] p-4">
                <p className="text-sm text-ink/45">Claims in window</p>
                <p className="mt-2 text-2xl font-bold text-[#173126]">{claimStats?.total_claims ?? 0}</p>
                <p className="mt-2 text-sm text-ink/55">Approval rate {formatPercent(claimStats?.approval_rate)}</p>
              </div>
              <div className="panel-quiet rounded-[22px] p-4">
                <p className="text-sm text-ink/45">Payout volume</p>
                <p className="mt-2 text-2xl font-bold text-[#173126]">{formatCurrency(payoutStats?.total_amount)}</p>
                <p className="mt-2 text-sm text-ink/55">{payoutStats?.total_payouts ?? 0} transfers</p>
              </div>
            </div>
            <div className="mt-4 rounded-[22px] bg-[#f4f4ef] p-4">
              <p className="text-sm text-ink/45">Scheduler cadence</p>
              <p className="mt-2 text-lg font-semibold text-[#173126]">
                {scheduler?.interval_seconds || "--"} second interval · next run{" "}
                {scheduler?.next_scheduled_at ? formatDateTime(scheduler.next_scheduled_at) : "--"}
              </p>
            </div>
          </div>

          <div className="panel p-6">
            <p className="eyebrow">Current signal snapshots</p>
            <div className="mt-4 space-y-3">
              {snapshotSummary.map((snapshot) => (
                <div key={snapshot.zone} className="panel-quiet rounded-[22px] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-[#173126]">{humanizeSlug(snapshot.zone)}</p>
                    <span className="pill bg-white text-ink/60">{snapshot.triggers_active.length} triggers</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-ink/65">
                    {snapshot.triggers_active.length ? snapshot.triggers_active.map(humanizeSlug).join(", ") : "No active threshold breaches"}
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
