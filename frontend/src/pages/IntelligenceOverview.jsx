import { useEffect, useState } from "react";
import { Activity, BrainCircuit, Clock3, MapPinned, ShieldAlert } from "lucide-react";

import { analyticsApi } from "../api/analytics";
import { healthApi } from "../api/health";
import { locationsApi } from "../api/locations";
import SectionHeader from "../components/SectionHeader";
import { formatDateTime, formatPercent, humanizeSlug } from "../utils/formatters";

export default function IntelligenceOverview() {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [config, setConfig] = useState(null);
  const [locations, setLocations] = useState(null);

  useEffect(() => {
    document.title = "System Intelligence | RideShield";
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [analyticsRes, configRes, locationsRes] = await Promise.all([
          analyticsApi.adminOverview({ days: 14 }),
          healthApi.getConfig(),
          locationsApi.config(),
        ]);
        setAnalytics(analyticsRes.data);
        setConfig(configRes.data);
        setLocations(locationsRes.data);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  if (loading) {
    return <div className="panel p-8 text-center text-ink/60">Loading intelligence overview...</div>;
  }

  const scheduler = config?.scheduler;

  return (
    <div className="space-y-12">
      <section className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="hero-glow hero-mesh rounded-[36px] p-8 sm:p-10">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-white/60">System intelligence</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-bold leading-tight sm:text-5xl">
            The logic layer behind RideShield, exposed as a readable product surface.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-white/78 sm:text-lg">
            RideShield should show how it monitors zones, evaluates signals, groups incidents, and turns those events into
            explainable worker outcomes instead of hiding the logic behind a black-box product surface.
          </p>
        </div>

        <div className="space-y-4">
          <div className="panel p-6">
            <p className="eyebrow">Scheduler state</p>
            <p className="mt-3 text-2xl font-bold text-primary">{scheduler?.enabled ? "Monitoring active" : "Monitoring disabled"}</p>
            <p className="mt-3 text-sm leading-7 text-on-surface-variant">
              Interval {scheduler?.interval_seconds || "--"}s · last finished {scheduler?.last_finished_at ? formatDateTime(scheduler.last_finished_at) : "--"} · next scheduled{" "}
              {scheduler?.next_scheduled_at ? formatDateTime(scheduler.next_scheduled_at) : "--"}
            </p>
          </div>
          <div className="panel-quiet p-6">
            <p className="text-sm text-on-surface-variant">Active geography</p>
            <p className="mt-2 text-lg font-semibold text-primary">{(locations?.cities || []).map((city) => city.display_name).join(", ")}</p>
          </div>
        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Intelligence blocks"
          title="What the system is reasoning over"
          description="These are the main decision layers that turn raw signals into worker-visible outcomes."
        />
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {[
            {
              icon: Activity,
              title: "Trigger signals",
              body: "Rain, heat, AQI, traffic, platform outage, and social disruption signals are read and evaluated against thresholds.",
            },
            {
              icon: MapPinned,
              title: "Zone awareness",
              body: "Cities and zones are DB-backed so monitoring, claim eligibility, and alerting all reference the same geography layer.",
            },
            {
              icon: ShieldAlert,
              title: "Fraud and trust",
              body: "Fraud score, trust score, and decision breakdown combine to reduce false positives and explain review pressure.",
            },
            {
              icon: BrainCircuit,
              title: "Decision output",
              body: "Each worker gets one claim per incident window, with approval, delay, or rejection exposed as a readable path.",
            },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="panel p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-[18px] bg-surface-container-low text-primary">
                <Icon size={22} />
              </div>
              <h3 className="mt-5 text-xl font-bold text-primary">{title}</h3>
              <p className="mt-3 text-sm leading-7 text-on-surface-variant">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Current readings"
          title="Current system-level indicators"
          description="These values come from the running backend so the page is not just a static explanation."
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="panel p-6">
            <p className="eyebrow">Loss ratio</p>
            <p className="mt-4 text-3xl font-bold text-primary">{formatPercent(analytics?.loss_ratio, 1)}</p>
          </div>
          <div className="panel p-6">
            <p className="eyebrow">Fraud rate</p>
            <p className="mt-4 text-3xl font-bold text-primary">{formatPercent(analytics?.fraud_rate, 1)}</p>
          </div>
          <div className="panel p-6">
            <p className="eyebrow">Activity index</p>
            <p className="mt-4 text-3xl font-bold text-primary">{analytics?.worker_activity_index ?? "--"}</p>
          </div>
          <div className="panel p-6">
            <p className="eyebrow">Cities monitored</p>
            <p className="mt-4 text-3xl font-bold text-primary">{(locations?.cities || []).length}</p>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="panel p-6">
            <p className="eyebrow">Forecast bands</p>
            <div className="mt-4 space-y-3">
              {(analytics?.next_week_forecast || []).map((entry) => (
                <div key={entry.city} className="rounded-[22px] bg-surface-container-low p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-primary">{humanizeSlug(entry.city)}</p>
                    <span className="pill bg-surface-container-lowest text-on-surface-variant">{entry.band}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    Base risk {entry.base_risk.toFixed(2)} · projected {entry.projected_risk.toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <Clock3 size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">Threshold notes</h3>
            </div>
            <div className="space-y-3 text-sm text-on-surface-variant">
              <p>Trigger evaluation is rule-based today and intentionally explainable.</p>
              <p>Claims are incident-based, not trigger-stacked, so overlapping same-window events do not multiply payouts for one worker.</p>
              <p>Location awareness is DB-backed, which keeps monitoring, claim logic, and future analytics tied to the same geography source of truth.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
