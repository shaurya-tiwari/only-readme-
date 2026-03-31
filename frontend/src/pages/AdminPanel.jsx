import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import EventPanel from "../components/EventPanel";
import DisruptionMap from "../components/DisruptionMap";
import ReviewQueue from "../components/ReviewQueue";
import SectionHeader from "../components/SectionHeader";
import StatCard from "../components/StatCard";
import { analyticsApi } from "../api/analytics";
import { claimsApi } from "../api/claims";
import { eventsApi } from "../api/events";
import { locationsApi } from "../api/locations";
import { payoutsApi } from "../api/payouts";
import { formatCurrency, formatPercent, humanizeSlug } from "../utils/formatters";

export default function AdminPanel() {
  const [selectedCity, setSelectedCity] = useState("all");
  const [cityOptions, setCityOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [claimStats, setClaimStats] = useState(null);
  const [payoutStats, setPayoutStats] = useState(null);
  const [queue, setQueue] = useState(null);
  const [events, setEvents] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);

  useEffect(() => {
    load();
    loadCities();
  }, []);

  async function loadCities() {
    const response = await locationsApi.cities();
    setCityOptions(response.data || []);
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
        reason: decision === "reject" ? "Rejected from Sprint 3 admin panel." : "Approved from Sprint 3 admin panel.",
      });
      await load();
    } finally {
      setResolvingId(null);
    }
  }

  const chartData = [
    { label: "Approved", value: claimStats?.approved || 0 },
    { label: "Delayed", value: claimStats?.delayed || 0 },
    { label: "Rejected", value: claimStats?.rejected || 0 },
  ];
  const visibleEvents = selectedCity === "all" ? events : events.filter((event) => event.city === selectedCity);

  if (loading) {
    return <div className="panel p-8 text-center text-ink/60">Loading admin panel...</div>;
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow="Admin controls"
        title="Claim operations and system health"
        description="This panel tracks throughput, fraud pressure, payout volume, and the delayed-claim review queue."
        action={
          <select className="field min-w-44" value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
            <option value="all">All cities</option>
            {cityOptions.map((city) => (
              <option key={city.id} value={city.slug}>
                {city.display_name}
              </option>
            ))}
          </select>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Claims in window" value={claimStats?.total_claims ?? 0} hint={`Approval rate ${formatPercent(claimStats?.approval_rate)}`} tone="storm" />
        <StatCard label="Fraud rate" value={formatPercent(claimStats?.fraud_rate)} hint="Current detection window" tone="ember" />
        <StatCard label="Payout volume" value={formatCurrency(payoutStats?.total_amount)} hint={`${payoutStats?.total_payouts ?? 0} transfers`} tone="forest" />
        <StatCard label="Review queue" value={queue?.total_pending ?? 0} hint={`${queue?.overdue_count ?? 0} overdue`} tone="gold" />
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Average final score" value={claimStats?.avg_final_score ?? "--"} hint={`Delayed rate ${formatPercent(claimStats?.delayed_rate)}`} tone="ink" />
        <StatCard label="Average fraud score" value={claimStats?.avg_fraud_score ?? "--"} hint="Lower is healthier" tone="ink" />
        <StatCard label="Loss ratio" value={formatPercent(analytics?.loss_ratio, 1)} hint={`Premiums in force ${formatCurrency(analytics?.premiums_in_force)}`} tone="ink" />
        <StatCard label="Activity index" value={analytics?.worker_activity_index ?? "--"} hint="Recent movement density" tone="ink" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="panel p-6">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Decision mix</p>
            <h3 className="mt-1 text-2xl font-bold">Claim status distribution</h3>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="claimsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#274d75" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#274d75" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(18,22,33,0.08)" />
                <XAxis dataKey="label" stroke="rgba(18,22,33,0.5)" />
                <YAxis stroke="rgba(18,22,33,0.5)" />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="#274d75" fill="url(#claimsGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <EventPanel events={visibleEvents.slice(0, 8)} />
      </div>

      <DisruptionMap events={visibleEvents} city={selectedCity} />

      <ReviewQueue claims={queue?.claims || []} resolvingId={resolvingId} onResolve={handleResolve} />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-6">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Duplicate claim log</p>
            <h3 className="mt-1 text-2xl font-bold">Dedup and extension audit trail</h3>
          </div>
          <div className="space-y-3">
            {analytics?.duplicate_claim_log?.length ? (
              analytics.duplicate_claim_log.map((entry) => (
                <div key={entry.id} className="rounded-2xl bg-black/[0.03] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold">{entry.action === "duplicate_detected" ? "Duplicate stopped" : "Incident extended"}</p>
                    <span className="pill bg-black/[0.05] text-ink/60">{humanizeSlug(entry.details?.zone || "system")}</span>
                  </div>
                  <p className="mt-2 text-sm text-ink/65">
                    {(entry.details?.incident_triggers || entry.details?.fired_triggers || []).length
                      ? (entry.details.incident_triggers || entry.details.fired_triggers).map(humanizeSlug).join(", ")
                      : "No trigger list"}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-ink/55">No recent duplicate or extension activity in the selected window.</p>
            )}
          </div>
        </div>

        <div className="panel p-6">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Next-week forecast</p>
            <h3 className="mt-1 text-2xl font-bold">Rule-based risk outlook</h3>
          </div>
          <div className="space-y-3">
            <div className="rounded-2xl bg-storm/8 p-4">
              <p className="text-sm font-semibold">Scheduler</p>
              <p className="mt-2 text-sm text-ink/65">
                {analytics?.scheduler?.enabled ? "Enabled" : "Disabled"} · interval {analytics?.scheduler?.interval_seconds || "--"}s · runs {analytics?.scheduler?.run_count || 0}
              </p>
            </div>
            {analytics?.next_week_forecast?.map((entry) => (
              <div key={entry.city} className="rounded-2xl bg-black/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold capitalize">{entry.city}</p>
                  <span className="pill bg-black/[0.05] text-ink/60">{entry.band}</span>
                </div>
                <p className="mt-2 text-sm text-ink/65">
                  Base risk {entry.base_risk.toFixed(2)} · active incidents {entry.active_incidents} · projected {entry.projected_risk.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
