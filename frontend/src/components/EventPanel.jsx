import { formatDateTime, formatPercent, humanizeSlug, statusPill } from "../utils/formatters";

export default function EventPanel({ events = [] }) {
  return (
    <div className="panel p-6">
      <div className="mb-5">
        <p className="eyebrow">Live disruption feed</p>
        <h3 className="mt-2 text-2xl font-bold text-[#173126]">Active incidents</h3>
        <p className="mt-2 text-sm leading-6 text-ink/60">
          RideShield watches signal clusters in the background, merges overlapping triggers into one incident, and turns
          that incident into an explainable claim path.
        </p>
      </div>

      <div className="space-y-3">
        {events.length ? (
          events.map((event) => {
            const triggers = event.metadata_json?.fired_triggers || [event.event_type];
            const confidence = event.event_confidence ? Number(event.event_confidence) * 100 : null;

            return (
              <div key={event.id} className="panel-quiet rounded-[24px] p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className={statusPill(event.status)}>{humanizeSlug(event.status)}</span>
                      <p className="text-sm font-semibold text-[#173126]">{triggers.map(humanizeSlug).join(", ")}</p>
                    </div>
                    <p className="mt-2 text-sm text-ink/60">
                      {humanizeSlug(event.zone)} · {humanizeSlug(event.city)}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-ink/55">
                      Threshold breaches in the same zone and time window were merged into one incident so the worker
                      experiences one coherent claim story instead of duplicate event noise.
                    </p>
                  </div>

                  <div className="text-right text-sm">
                    <p className="font-semibold text-[#173126]">{formatPercent((event.disruption_score || 0) * 100)}</p>
                    <p className="mt-1 text-ink/45">{formatDateTime(event.started_at)}</p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-xs text-ink/55">
                  <span className="pill bg-white text-ink/60">Triggers {triggers.length}</span>
                  {confidence !== null ? <span className="pill bg-white text-ink/60">Confidence {formatPercent(confidence)}</span> : null}
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
