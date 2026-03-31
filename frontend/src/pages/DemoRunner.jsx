import { useEffect, useMemo, useState } from "react";

import ScenarioCard from "../components/ScenarioCard";
import SectionHeader from "../components/SectionHeader";
import StatCard from "../components/StatCard";
import { claimsApi } from "../api/claims";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import { policiesApi } from "../api/policies";
import { triggersApi } from "../api/triggers";
import { workersApi } from "../api/workers";
import { SCENARIOS } from "../utils/constants";
import { formatCurrency, formatDateTime, formatPercent, formatRelative, humanizeSlug } from "../utils/formatters";

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
      await triggersApi.scenario(scenarioId);
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

  const snapshotSummary = useMemo(() => (status?.snapshots || []).slice(0, 4), [status]);
  const scheduler = config?.scheduler;

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Demo runner"
        title="Scenario control surface"
        description="Use the live trigger APIs to move the backend through the Sprint 2 demo narratives and inspect the resulting claim and payout totals."
        action={
          <div className="flex flex-wrap gap-3">
            <select className="field min-w-44" value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
              {locations.cities.map((city) => (
                <option key={city.id} value={city.slug}>
                  {city.display_name}
                </option>
              ))}
            </select>
            <button type="button" className="button-secondary" onClick={createDemoWorker} disabled={setupLoading}>
              {setupLoading ? "Creating..." : "Create demo worker"}
            </button>
            <button type="button" className="button-secondary" onClick={handleReset}>
              Reset simulators
            </button>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Claims" value={claimStats?.total_claims ?? 0} hint={`Approval rate ${formatPercent(claimStats?.approval_rate)}`} tone="storm" />
        <StatCard label="Fraud rate" value={formatPercent(claimStats?.fraud_rate)} hint="Scenario-adjusted" tone="ember" />
        <StatCard label="Payout volume" value={formatCurrency(payoutStats?.total_amount)} hint={`${payoutStats?.total_payouts ?? 0} transfers`} tone="forest" />
        <StatCard label="Monitored zones" value={status?.zones_checked ?? 0} hint={`Trigger status for ${humanizeSlug(selectedCity)}`} tone="gold" />
      </div>

      <div className="panel p-6">
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Monitoring loop</p>
          <h3 className="mt-1 text-2xl font-bold">Scheduler visibility</h3>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl bg-black/[0.03] p-4">
            <p className="text-sm text-ink/45">Status</p>
            <p className="mt-2 font-semibold">{scheduler?.enabled ? "Monitoring active" : "Monitoring disabled"}</p>
          </div>
          <div className="rounded-2xl bg-black/[0.03] p-4">
            <p className="text-sm text-ink/45">Last run</p>
            <p className="mt-2 font-semibold">{scheduler?.last_finished_at ? formatRelative(scheduler.last_finished_at) : "--"}</p>
          </div>
          <div className="rounded-2xl bg-black/[0.03] p-4">
            <p className="text-sm text-ink/45">Next run</p>
            <p className="mt-2 font-semibold">{scheduler?.next_scheduled_at ? formatRelative(scheduler.next_scheduled_at) : "--"}</p>
          </div>
          <div className="rounded-2xl bg-black/[0.03] p-4">
            <p className="text-sm text-ink/45">Interval</p>
            <p className="mt-2 font-semibold">{scheduler?.interval_seconds || "--"}s</p>
          </div>
        </div>
        <p className="mt-4 text-sm text-ink/60">
          RideShield is not waiting for a worker to file a claim. The scheduler keeps checking signals in the background and the demo runner is an explicit admin override for showing cause and effect on demand in {humanizeSlug(selectedCity)}.
        </p>
        {scheduler?.last_finished_at ? (
          <p className="mt-2 text-xs text-ink/45">
            Last completed at {formatDateTime(scheduler.last_finished_at)}
          </p>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
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

      <div className="panel p-6">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Live snapshots</p>
          <h3 className="mt-1 text-2xl font-bold">Current trigger thresholds by zone</h3>
          <p className="mt-2 text-sm text-ink/60">Live signal snapshots for {humanizeSlug(selectedCity)}.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {snapshotSummary.map((snapshot) => (
            <div key={snapshot.zone} className="rounded-2xl bg-black/[0.03] p-4">
              <p className="text-sm font-semibold">{humanizeSlug(snapshot.zone)}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.2em] text-ink/45">Active triggers</p>
              <p className="mt-2 text-sm text-ink/70">{snapshot.triggers_active.length ? snapshot.triggers_active.map(humanizeSlug).join(", ") : "None"}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
