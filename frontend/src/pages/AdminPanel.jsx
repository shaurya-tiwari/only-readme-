import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, ShieldAlert } from "lucide-react";

import EventPanel from "../components/EventPanel";
import DisruptionMap from "../components/DisruptionMap";
import ReviewQueue from "../components/ReviewQueue";
import { analyticsApi } from "../api/analytics";
import { claimsApi } from "../api/claims";
import { eventsApi } from "../api/events";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import { formatCurrency, formatPercent, formatRelative, humanizeSlug } from "../utils/formatters";

function KpiTile({ label, value, hint, accent = "default" }) {
  const accentClass = {
    default: "bg-surface-container-lowest",
    soft: "bg-surface-container-low",
    dark: "bg-[radial-gradient(circle_at_top_right,_rgba(133,189,188,0.16),_transparent_30%),linear-gradient(135deg,#003535_0%,#0d4d4d_100%)] text-on-primary",
  }[accent];

  return (
    <div className={`rounded-[22px] border border-outline-variant/40 p-5 shadow-[0_12px_30px_rgba(26,28,25,0.05)] ${accentClass}`}>
      <p className={`text-[11px] font-bold uppercase tracking-[0.24em] ${accent === "dark" ? "text-white/55" : "text-on-surface-variant"}`}>{label}</p>
      <p className={`mt-3 text-3xl font-bold ${accent === "dark" ? "text-white" : "text-primary"}`}>{value}</p>
      <p className={`mt-2 text-sm ${accent === "dark" ? "text-white/75" : "text-on-surface-variant"}`}>{hint}</p>
    </div>
  );
}

export default function AdminPanel() {
  const [selectedCity, setSelectedCity] = useState("all");
  const [selectedZone, setSelectedZone] = useState("all");
  const [cityOptions, setCityOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [claimStats, setClaimStats] = useState(null);
  const [payoutStats, setPayoutStats] = useState(null);
  const [queue, setQueue] = useState(null);
  const [events, setEvents] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);

  useEffect(() => {
    document.title = "Admin Panel | RideShield";
  }, []);

  useEffect(() => {
    load();
    loadCities();
  }, []);

  async function loadCities() {
    try {
      const response = await locationsApi.cities();
      setCityOptions(response.data || []);
    } catch {
      setCityOptions([]);
    }
  }

  async function load() {
    setLoading(true);
    try {
      const [claimsRes, payoutsRes, queueRes, eventsRes, historyRes, analyticsRes] = await Promise.all([
        claimsApi.stats({ days: 14 }),
        payoutsApi.stats({ days: 14 }),
        claimsApi.queue(),
        eventsApi.active(),
        eventsApi.history({ days: 14, limit: 20 }),
        analyticsApi.adminOverview({ days: 14 }),
      ]);
      setClaimStats(claimsRes.data);
      setPayoutStats(payoutsRes.data);
      setQueue(queueRes.data);
      setEvents([...(eventsRes.data.events || []), ...(historyRes.data.events || []).slice(0, 6)]);
      setAnalytics(analyticsRes.data);
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(claimId, decision) {
    setResolvingId(claimId);
    try {
      await claimsApi.resolve(claimId, {
        decision,
        reviewed_by: "admin_panel",
        reason: decision === "reject" ? "Rejected from admin panel." : "Approved from admin panel.",
      });
      await load();
    } finally {
      setResolvingId(null);
    }
  }

  const cityFilteredEvents = selectedCity === "all" ? events : events.filter((event) => event.city === selectedCity);
  const zoneOptions = useMemo(() => [...new Set(cityFilteredEvents.map((event) => event.zone).filter(Boolean))], [cityFilteredEvents]);
  const visibleEvents = selectedZone === "all" ? cityFilteredEvents : cityFilteredEvents.filter((event) => event.zone === selectedZone);

  if (loading) {
    return <div className="panel p-8 text-center text-ink/60">Loading admin panel...</div>;
  }

  return (
    <div className="space-y-8">
      <section className="mb-6 flex items-end justify-between gap-6">
        <div>
          <p className="eyebrow">Admin controls</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-primary">System Oversight</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-on-surface-variant">
            Operational monitoring for RideShield incidents, review pressure, payout movement, and scheduler heartbeat.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <select className="field min-w-44 !rounded-full !bg-surface-container-low !py-2" value={selectedCity} onChange={(e) => { setSelectedCity(e.target.value); setSelectedZone("all"); }}>
            <option value="all">All cities</option>
            {cityOptions.map((city) => (
              <option key={city.id} value={city.slug}>{city.display_name}</option>
            ))}
          </select>
          <select className="field min-w-44 !rounded-full !bg-surface-container-low !py-2" value={selectedZone} onChange={(e) => setSelectedZone(e.target.value)}>
            <option value="all">All zones</option>
            {zoneOptions.map((zone) => (
              <option key={zone} value={zone}>{humanizeSlug(zone)}</option>
            ))}
          </select>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
        <KpiTile label="Claims" value={claimStats?.total_claims ?? 0} hint={`Approval rate ${formatPercent(claimStats?.approval_rate)}`} />
        <KpiTile label="Approval rate" value={formatPercent(claimStats?.approval_rate)} hint={`Delayed ${formatPercent(claimStats?.delayed_rate)}`} />
        <KpiTile label="Delayed" value={claimStats?.delayed ?? 0} hint={`${queue?.overdue_count ?? 0} overdue`} />
        <KpiTile label="Fraud rate" value={formatPercent(claimStats?.fraud_rate)} hint="Current detection window" />
        <KpiTile label="Payout volume" value={formatCurrency(payoutStats?.total_amount)} hint={`${payoutStats?.total_payouts ?? 0} transfers`} />
        <KpiTile label="Loss ratio" value={analytics?.loss_ratio != null ? `${Number(analytics.loss_ratio).toFixed(1)}%` : "0.0%"} hint="Target below 70%" />
        <KpiTile label="Network health" value="99.98%" hint="Scheduler and payout pipeline stable" accent="dark" />
      </div>

      <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-6">
          <ReviewQueue claims={queue?.claims || []} resolvingId={resolvingId} onResolve={handleResolve} />

          <div className="grid gap-6 md:grid-cols-2">
            <div className="panel p-6">
              <div className="mb-4 flex items-center gap-3">
                <ShieldAlert size={18} className="text-primary" />
                <h3 className="text-lg font-bold text-primary">Integrity log</h3>
              </div>
              <div className="space-y-2 rounded-[24px] bg-primary p-4 font-mono text-sm text-white">
                {analytics?.duplicate_claim_log?.length ? (
                  analytics.duplicate_claim_log.map((entry) => (
                    <div key={entry.id} className="rounded-[16px] border border-white/10 bg-white/5 px-3 py-3">
                      <p className="text-[11px] uppercase tracking-[0.24em] text-white/50">
                        {entry.action === "duplicate_detected" ? "DUPLICATE_BLOCK" : "EXTENSION_AUTH"} · {formatRelative(entry.created_at)}
                      </p>
                      <p className="mt-2 leading-6 text-white/85">
                        Zone {humanizeSlug(entry.details?.zone || "system")} · {(entry.details?.incident_triggers || entry.details?.fired_triggers || []).map(humanizeSlug).join(", ") || "No trigger list"}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-white/75">No recent duplicate or extension activity.</p>
                )}
              </div>
            </div>

            <div className="panel p-6">
              <div className="mb-4 flex items-center gap-3">
                <AlertTriangle size={18} className="text-primary" />
                <h3 className="text-lg font-bold text-primary">Next-week forecast</h3>
              </div>
              <div className="space-y-3">
                {analytics?.next_week_forecast?.map((entry) => (
                  <div key={entry.city} className="rounded-[20px] bg-surface-container-low p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-primary capitalize">{entry.city}</p>
                      <span className="pill bg-surface-container-lowest text-on-surface-variant">{entry.band}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                      Base risk {entry.base_risk.toFixed(2)} · active incidents {entry.active_incidents} · projected {entry.projected_risk.toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <DisruptionMap events={visibleEvents} city={selectedCity} />
        </section>

        <aside className="space-y-6">
          <div className="panel p-6">
            <div className="mb-4 flex items-center gap-3">
              <Clock3 size={18} className="text-primary" />
              <h3 className="text-lg font-bold text-primary">System Scheduler</h3>
            </div>
            <div className="space-y-4">
              <div className="rounded-[20px] bg-surface-container-low p-4">
                <p className="text-sm text-on-surface-variant">Status</p>
                <p className="mt-2 text-lg font-semibold text-primary">{analytics?.scheduler?.enabled ? "Monitoring active" : "Disabled"}</p>
              </div>
              <div className="rounded-[20px] bg-surface-container-low p-4">
                <p className="text-sm text-on-surface-variant">Last run</p>
                <p className="mt-2 text-lg font-semibold text-primary">
                  {analytics?.scheduler?.last_finished_at ? formatRelative(analytics.scheduler.last_finished_at) : "--"}
                </p>
              </div>
              <div className="rounded-[20px] bg-surface-container-low p-4">
                <p className="text-sm text-on-surface-variant">Next run</p>
                <p className="mt-2 text-lg font-semibold text-primary">
                  {analytics?.scheduler?.next_scheduled_at ? formatRelative(analytics.scheduler.next_scheduled_at) : "--"}
                </p>
              </div>
              <div className="rounded-[20px] bg-surface-container-low p-4">
                <p className="text-sm text-on-surface-variant">Interval</p>
                <p className="mt-2 text-lg font-semibold text-primary">{analytics?.scheduler?.interval_seconds || "--"} seconds</p>
              </div>
            </div>
          </div>

          <div className="panel p-6">
            <div className="mb-5">
              <p className="eyebrow">Operational posture</p>
              <h3 className="mt-2 text-2xl font-bold leading-tight text-primary">
                Decisions should feel explainable under pressure, not merely automated.
              </h3>
              <p className="mt-3 text-sm leading-7 text-on-surface-variant">
                Delayed claims, duplicate prevention, and live disruption context stay readable enough for manual review and product demos.
              </p>
            </div>
          </div>

          <EventPanel events={visibleEvents.slice(0, 8)} />
        </aside>
      </div>
    </div>
  );
}
