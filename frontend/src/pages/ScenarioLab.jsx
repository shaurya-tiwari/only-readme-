import { useEffect, useMemo, useState } from "react";
import { FlaskConical, PlayCircle, Save, Trash2 } from "lucide-react";

import { locationsApi } from "../api/locations";
import { triggersApi } from "../api/triggers";
import { STORAGE_KEYS } from "../utils/constants";
import { formatCurrency, humanizeSlug } from "../utils/formatters";

const defaultScenario = {
  city: "delhi",
  zones: ["south_delhi"],
  signals: {
    rain_mm_hr: 10,
    temperature_c: 30,
    aqi_value: 180,
    congestion_index: 0.5,
    order_density_drop: 0.2,
  },
  worker: {
    seed_demo_worker: true,
    profile: "legit",
    plan_name: "smart_protect",
    platform: "zomato",
    self_reported_income: 900,
    working_hours: 8,
  },
  execution: {
    mode: "single",
    runs: 1,
  },
};

const fallbackCities = [
  { id: 1, slug: "delhi", display_name: "Delhi" },
  { id: 2, slug: "mumbai", display_name: "Mumbai" },
  { id: 3, slug: "bengaluru", display_name: "Bengaluru" },
  { id: 4, slug: "hyderabad", display_name: "Hyderabad" },
  { id: 5, slug: "chennai", display_name: "Chennai" },
  { id: 6, slug: "pune", display_name: "Pune" },
  { id: 7, slug: "kolkata", display_name: "Kolkata" },
];

const planOptions = [
  { value: "basic_protect", label: "Basic Protect" },
  { value: "smart_protect", label: "Smart Protect" },
  { value: "assured_plan", label: "Assured Plan" },
  { value: "pro_max", label: "Pro Max" },
];

const platformOptions = [
  { value: "zomato", label: "Zomato" },
  { value: "swiggy", label: "Swiggy" },
  { value: "blinkit", label: "Blinkit" },
  { value: "dunzo", label: "Dunzo" },
];

const profileOptions = [
  { value: "legit", label: "Stable worker" },
  { value: "edge", label: "Borderline worker" },
  { value: "fraud", label: "Suspicious worker" },
];

function loadPresets() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEYS.scenarioLabPresets);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function savePresets(presets) {
  window.localStorage.setItem(STORAGE_KEYS.scenarioLabPresets, JSON.stringify(presets));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function buildTriggerSummary(run) {
  const counts = new Map();
  for (const detail of run?.details || []) {
    for (const trigger of detail.triggers_fired || []) {
      counts.set(trigger, (counts.get(trigger) || 0) + 1);
    }
  }
  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
}

export default function ScenarioLab() {
  const [scenario, setScenario] = useState(defaultScenario);
  const [locations, setLocations] = useState({ cities: [], zones: [] });
  const [presets, setPresets] = useState([]);
  const [presetName, setPresetName] = useState("");
  const [running, setRunning] = useState(false);
  const [citiesLoading, setCitiesLoading] = useState(true);
  const [result, setResult] = useState(null);

  useEffect(() => {
    document.title = "Scenario Lab | RideShield";
    setPresets(loadPresets());
  }, []);

  useEffect(() => {
    async function loadCities() {
      setCitiesLoading(true);
      try {
        const response = await locationsApi.cities();
        const cities = response.data || [];
        setLocations((current) => ({ ...current, cities: cities.length ? cities : fallbackCities }));
      } catch {
        setLocations((current) => ({ ...current, cities: fallbackCities }));
      } finally {
        setCitiesLoading(false);
      }
    }
    loadCities();
  }, []);

  useEffect(() => {
    async function loadZones() {
      if (!scenario.city) {
        setLocations((current) => ({ ...current, zones: [] }));
        return;
      }
      const response = await locationsApi.zones(scenario.city);
      setLocations((current) => ({ ...current, zones: response.data || [] }));
    }
    loadZones();
  }, [scenario.city]);

  const cityZones = useMemo(
    () => locations.zones.filter((zone) => zone.city_slug === scenario.city),
    [locations.zones, scenario.city],
  );

  useEffect(() => {
    if (!cityZones.length) {
      return;
    }
    const validZones = scenario.zones.filter((zone) => cityZones.some((item) => item.slug === zone));
    if (!validZones.length) {
      setScenario((current) => ({
        ...current,
        zones: [cityZones[0].slug],
      }));
    } else if (validZones.length !== scenario.zones.length) {
      setScenario((current) => ({ ...current, zones: validZones }));
    }
  }, [cityZones, scenario.zones]);

  function updateScenario(path, value) {
    setScenario((current) => {
      const next = structuredClone(current);
      let target = next;
      for (let i = 0; i < path.length - 1; i += 1) {
        target = target[path[i]];
      }
      target[path[path.length - 1]] = value;
      return next;
    });
  }

  function toggleZone(zone) {
    setScenario((current) => {
      const nextZones = current.zones.includes(zone)
        ? current.zones.filter((item) => item !== zone)
        : [...current.zones, zone];
      return {
        ...current,
        zones: nextZones.length ? nextZones : [zone],
      };
    });
  }

  async function runLab() {
    setRunning(true);
    try {
      const payload = {
        ...scenario,
        execution: {
          ...scenario.execution,
          runs: scenario.execution.mode === "batch" ? scenario.execution.runs : 1,
        },
        preset_name: presetName || null,
      };
      const response = await triggersApi.labRun(payload);
      setResult(response.data);
    } finally {
      setRunning(false);
    }
  }

  function handleSavePreset() {
    if (!presetName.trim()) {
      return;
    }
    const next = [
      { name: presetName.trim(), config: scenario },
      ...presets.filter((preset) => preset.name !== presetName.trim()),
    ].slice(0, 12);
    setPresets(next);
    savePresets(next);
  }

  function handleLoadPreset(preset) {
    setPresetName(preset.name);
    setScenario(preset.config);
  }

  function handleDeletePreset(name) {
    const next = presets.filter((preset) => preset.name !== name);
    setPresets(next);
    savePresets(next);
  }

  const aggregate = result?.aggregate;
  const latestRun = result?.runs?.[result.runs.length - 1];
  const triggerSummary = buildTriggerSummary(latestRun);

  return (
    <div className="space-y-8">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <p className="eyebrow">Scenario Lab</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-primary">Controlled exploration surface</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-on-surface-variant">
            Compose signal pressure, seed a controlled worker profile, and run exploratory trigger cycles through the same
            engine used by the live demo and admin flows.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" className="button-primary !rounded-full !px-6 !py-2.5" disabled={running} onClick={runLab}>
            <PlayCircle size={16} />
            {running ? "Running..." : "Run lab"}
          </button>
          <div className="hidden items-center gap-2 rounded-[18px] bg-surface-container-low px-4 py-3 text-xs font-bold uppercase tracking-[0.24em] text-on-surface-variant lg:flex">
            <FlaskConical size={14} />
            Exploration only
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <section className="space-y-6">

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="context-panel p-6">
              <p className="eyebrow">Environment</p>
              <h3 className="mt-2 text-lg font-bold text-primary">Compose signal pressure</h3>
              <div className="mt-5 space-y-4">
                <div>
                  <label className="text-sm text-on-surface-variant">City</label>
                  <select
                    className="field mt-2"
                    value={scenario.city}
                    onChange={(e) => updateScenario(["city"], e.target.value)}
                    disabled={citiesLoading}
                  >
                    {citiesLoading ? (
                      <option value="">Loading cities...</option>
                    ) : (locations.cities || []).map((city) => (
                      <option key={city.id} value={city.slug}>{city.display_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-on-surface-variant">Zones</label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {cityZones.map((zone) => (
                      <button
                        key={zone.slug}
                        type="button"
                        className={`pill ${scenario.zones.includes(zone.slug) ? "badge-active" : "badge-guarded"}`}
                        onClick={() => toggleZone(zone.slug)}
                      >
                        {zone.display_name}
                      </button>
                    ))}
                  </div>
                </div>
                {[
                  ["rain_mm_hr", "Rain mm/hr", 0, 80, 1],
                  ["temperature_c", "Temperature C", 0, 50, 1],
                  ["aqi_value", "AQI", 0, 500, 10],
                  ["congestion_index", "Traffic", 0, 1, 0.05],
                  ["order_density_drop", "Platform drop", 0, 1, 0.05],
                ].map(([key, label, min, max, step]) => (
                  <div key={key}>
                    <div className="flex items-center justify-between gap-3">
                      <label className="text-sm text-on-surface-variant">{label}</label>
                      <span className="pill-subtle">{scenario.signals[key]}</span>
                    </div>
                    <input
                      className="mt-2 w-full"
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={scenario.signals[key]}
                      onChange={(e) => updateScenario(["signals", key], Number(e.target.value))}
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="context-panel p-6">
              <p className="eyebrow">Worker profile</p>
              <h3 className="mt-2 text-lg font-bold text-primary">Seed a controlled claimant</h3>
              <div className="mt-5 space-y-4">
                <label className="flex items-center gap-3 text-sm text-on-surface-variant">
                  <input
                    type="checkbox"
                    checked={scenario.worker.seed_demo_worker}
                    onChange={(e) => updateScenario(["worker", "seed_demo_worker"], e.target.checked)}
                  />
                  Seed demo worker for the run
                </label>
                <div>
                  <label className="text-sm text-on-surface-variant">Behavior profile</label>
                  <select
                    className="field mt-2"
                    value={scenario.worker.profile}
                    onChange={(e) => updateScenario(["worker", "profile"], e.target.value)}
                  >
                    {profileOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-on-surface-variant">Plan</label>
                  <select
                    className="field mt-2"
                    value={scenario.worker.plan_name}
                    onChange={(e) => updateScenario(["worker", "plan_name"], e.target.value)}
                  >
                    {planOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-on-surface-variant">Platform</label>
                  <select
                    className="field mt-2"
                    value={scenario.worker.platform}
                    onChange={(e) => updateScenario(["worker", "platform"], e.target.value)}
                  >
                    {platformOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-sm text-on-surface-variant">Income</label>
                    <input
                      className="field mt-2"
                      type="number"
                      min="100"
                      step="50"
                      value={scenario.worker.self_reported_income}
                      onChange={(e) => updateScenario(["worker", "self_reported_income"], Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-on-surface-variant">Hours</label>
                    <input
                      className="field mt-2"
                      type="number"
                      min="1"
                      max="16"
                      value={scenario.worker.working_hours}
                      onChange={(e) => updateScenario(["worker", "working_hours"], clamp(Number(e.target.value), 1, 16))}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="context-panel p-6">
            <p className="eyebrow">Execution</p>
            <h3 className="mt-2 text-lg font-bold text-primary">Single run or distribution sample</h3>
            <div className="mt-5 grid gap-4 md:grid-cols-[0.7fr_0.3fr_auto]">
              <div>
                <label className="text-sm text-on-surface-variant">Mode</label>
                <select
                  className="field mt-2"
                  value={scenario.execution.mode}
                  onChange={(e) => updateScenario(["execution", "mode"], e.target.value)}
                >
                  <option value="single">Single run</option>
                  <option value="batch">Batch run</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-on-surface-variant">Runs</label>
                <input
                  className="field mt-2"
                  type="number"
                  min="1"
                  max="20"
                  value={scenario.execution.runs}
                  disabled={scenario.execution.mode !== "batch"}
                  onChange={(e) => updateScenario(["execution", "runs"], clamp(Number(e.target.value), 1, 20))}
                />
              </div>
              <div className="flex items-end">
                <button type="button" className="button-primary !rounded-full !px-6 !py-2.5" disabled={running} onClick={runLab}>
                  <PlayCircle size={16} />
                  {running ? "Running..." : "Run lab"}
                </button>
              </div>
            </div>
            <p className="mt-4 text-sm text-on-surface-variant">
              Scenario Lab uses the shared trigger and claim engine. Runs create simulation-only records in this working environment.
            </p>
          </div>

          <div className="decision-panel p-6">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <p className="eyebrow">Preset memory</p>
                <h2 className="mt-2 text-2xl font-bold text-primary">Save repeatable exploratory setups</h2>
              </div>
              <div className="flex flex-wrap gap-3">
                <input
                  className="field min-w-56 !rounded-full !py-2"
                  placeholder="Preset name"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                />
                <button type="button" className="button-secondary !rounded-full !px-5 !py-2" onClick={handleSavePreset}>
                  <Save size={16} />
                  Save preset
                </button>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {presets.length ? presets.map((preset) => (
                <div key={preset.name} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <button type="button" className="text-left font-semibold text-primary" onClick={() => handleLoadPreset(preset)}>
                      {preset.name}
                    </button>
                    <button type="button" className="pill-subtle" onClick={() => handleDeletePreset(preset.name)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <p className="mt-2 text-sm text-on-surface-variant">
                    {humanizeSlug(preset.config.city)} Â· {preset.config.zones.map(humanizeSlug).join(", ")}
                  </p>
                </div>
              )) : (
                <p className="text-sm text-on-surface-variant">No saved presets yet.</p>
              )}
            </div>
          </div>

        </section>

        <aside className="space-y-6">
          <div className="context-panel p-6">
            <button
              type="button"
              className="flex w-full items-center justify-between gap-3 text-left"
              onClick={() => setScenario((s) => ({ ...s, _showPayload: !s._showPayload }))}
            >
              <div>
                <p className="eyebrow">Scenario object</p>
                <h3 className="mt-2 text-lg font-bold text-primary">Structured input payload</h3>
              </div>
              <span className="pill-subtle">{scenario._showPayload ? 'Hide' : 'Show'}</span>
            </button>
            {scenario._showPayload ? (
              <pre className="mt-4 overflow-x-auto rounded-[20px] bg-surface-container-low p-4 text-xs leading-6 text-on-surface-variant">
                {JSON.stringify(scenario, null, 2)}
              </pre>
            ) : null}
          </div>

          <div className="context-panel p-6">
            <p className="eyebrow">Aggregate outcome</p>
            <h3 className="mt-2 text-lg font-bold text-primary">What the engine did</h3>
            {aggregate ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  ["Claims generated", aggregate.claims_generated],
                  ["Approved", aggregate.claims_approved],
                  ["Delayed", aggregate.claims_delayed],
                  ["Rejected", aggregate.claims_rejected],
                  ["Duplicates", aggregate.claims_duplicate],
                  ["Payout", formatCurrency(aggregate.total_payout)],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                    <p className="text-sm text-on-surface-variant">{label}</p>
                    <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-on-surface-variant">No exploratory run yet.</p>
            )}
          </div>

          <div className="context-panel p-6">
            <p className="eyebrow">Latest run</p>
            <h3 className="mt-2 text-lg font-bold text-primary">Trigger and claim inspection</h3>
            {latestRun ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                  <p className="text-sm text-on-surface-variant">Worker</p>
                  <p className="mt-2 font-semibold text-primary">
                    {latestRun.worker?.name || "No seeded worker"} {latestRun.worker?.profile ? `Â· ${humanizeSlug(latestRun.worker.profile)}` : ""}
                  </p>
                </div>
                <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                  <p className="text-sm text-on-surface-variant">Trigger summary</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {triggerSummary.length ? triggerSummary.map(([trigger, count]) => (
                      <span key={trigger} className="pill-subtle">{humanizeSlug(trigger)} Â· {count}</span>
                    )) : <span className="text-sm text-on-surface-variant">No triggers crossed.</span>}
                  </div>
                </div>
                <div className="rounded-[18px] border border-primary/8 bg-surface-container-low/80 p-4">
                  <p className="text-sm text-on-surface-variant">Zone details</p>
                  <div className="mt-3 space-y-3">
                    {(latestRun.details || []).map((detail) => (
                      <div key={detail.zone} className="rounded-[16px] border border-primary/6 bg-surface-container-high/60 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-semibold text-primary">{humanizeSlug(detail.zone)}</p>
                          <span className="pill-subtle">
                            {(detail.triggers_fired || []).length ? (detail.triggers_fired || []).map(humanizeSlug).join(", ") : "No triggers"}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-on-surface-variant">
                          Rain {detail.signals?.rain ?? 0} Â· Heat {detail.signals?.heat ?? 0} Â· AQI {detail.signals?.aqi ?? 0} Â· Traffic {detail.signals?.traffic ?? 0} Â· Platform {detail.signals?.platform_outage ?? 0}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-on-surface-variant">Run the lab to inspect outcomes.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
