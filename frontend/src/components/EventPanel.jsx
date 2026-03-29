import { formatDateTime, formatPercent, humanizeSlug, statusPill } from "../utils/formatters";

export default function EventPanel({ events = [] }) {
  return (
    <div className="panel p-6">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Live disruption feed</p>
        <h3 className="mt-1 text-2xl font-bold">Active events</h3>
      </div>
      <div className="space-y-3">
        {events.length ? (
          events.map((event) => {
            const triggers = event.metadata_json?.fired_triggers || [event.event_type];
            const confidence = event.event_confidence ? Number(event.event_confidence) * 100 : null;
            return (
              <div key={event.id} className="rounded-2xl bg-black/[0.03] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className={statusPill(event.status)}>{humanizeSlug(event.status)}</span>
                      <p className="text-sm font-semibold">{triggers.map(humanizeSlug).join(", ")}</p>
                    </div>
                    <p className="mt-2 text-sm text-ink/60">
                      {humanizeSlug(event.zone)} · {humanizeSlug(event.city)}
                    </p>
                    <p className="mt-2 text-sm text-ink/55">
                      Triggered because these live signals crossed threshold in the same zone and were merged into one incident.
                    </p>
                  </div>
                  <div className="text-right text-sm">
                    <p>{formatPercent((event.disruption_score || 0) * 100)}</p>
                    <p className="text-ink/45">{formatDateTime(event.started_at)}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-ink/55">
                  <span className="pill bg-white text-ink/60">Triggers: {triggers.length}</span>
                  {confidence !== null ? (
                    <span className="pill bg-white text-ink/60">Confidence {formatPercent(confidence)}</span>
                  ) : null}
                  <span className="pill bg-white text-ink/60">Claims {event.claims_generated}</span>
                </div>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-ink/55">No active disruptions right now.</p>
        )}
      </div>
    </div>
  );
}
