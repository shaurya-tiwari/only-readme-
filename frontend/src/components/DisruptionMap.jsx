import { humanizeSlug } from "../utils/formatters";

const ZONE_COORDS = {
  south_delhi: { top: "62%", left: "42%" },
  north_delhi: { top: "18%", left: "48%" },
  east_delhi: { top: "44%", left: "72%" },
  west_delhi: { top: "42%", left: "20%" },
  central_delhi: { top: "40%", left: "46%" },
  south_mumbai: { top: "78%", left: "36%" },
  western_suburbs: { top: "42%", left: "24%" },
  eastern_suburbs: { top: "46%", left: "64%" },
  navi_mumbai: { top: "36%", left: "78%" },
  koramangala: { top: "62%", left: "46%" },
  whitefield: { top: "32%", left: "76%" },
  indiranagar: { top: "42%", left: "58%" },
  jayanagar: { top: "70%", left: "40%" },
  electronic_city: { top: "84%", left: "52%" },
  t_nagar: { top: "50%", left: "40%" },
  anna_nagar: { top: "28%", left: "44%" },
  adyar: { top: "68%", left: "64%" },
  velachery: { top: "72%", left: "52%" },
};

function intensityClass(score) {
  if (score >= 0.75) {
    return "bg-rose-500";
  }
  if (score >= 0.5) {
    return "bg-orange-400";
  }
  if (score >= 0.25) {
    return "bg-gold";
  }
  return "bg-storm";
}

export default function DisruptionMap({ events = [], city = "delhi" }) {
  const zoneSummary = Object.values(
    events.reduce((acc, event) => {
      const current = acc[event.zone] || {
        zone: event.zone,
        count: 0,
        severity: 0,
        triggers: new Set(),
      };
      current.count += 1;
      current.severity = Math.max(current.severity, Number(event.severity || 0));
      const triggers = event.metadata_json?.fired_triggers || [event.event_type];
      triggers.forEach((trigger) => current.triggers.add(trigger));
      acc[event.zone] = current;
      return acc;
    }, {}),
  ).map((item) => ({
    ...item,
    triggers: Array.from(item.triggers),
  }));

  return (
    <div className="panel p-6">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink/45">Disruption map</p>
        <h3 className="mt-1 text-2xl font-bold">
          Zone heat view for {city === "all" ? "all monitored cities" : humanizeSlug(city)}
        </h3>
      </div>
      <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
        <div className="relative min-h-72 overflow-hidden rounded-[2rem] bg-[linear-gradient(180deg,rgba(235,236,231,1),rgba(214,218,214,1))] p-4">
          <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px)", backgroundSize: "36px 36px" }} />
          <div className="absolute inset-6 rounded-[1.75rem] border border-black/8" />
          <div className="absolute inset-[18%] rounded-[1.75rem] bg-[radial-gradient(circle_at_25%_30%,rgba(255,255,255,0.8),transparent_18%),radial-gradient(circle_at_70%_62%,rgba(255,255,255,0.55),transparent_16%),linear-gradient(135deg,rgba(68,72,72,0.10),rgba(68,72,72,0.03))]" />
          {zoneSummary.length ? (
            zoneSummary.map((zone) => {
              const coord = ZONE_COORDS[zone.zone] || { top: "50%", left: "50%" };
              return (
                <div
                  key={zone.zone}
                  className="absolute -translate-x-1/2 -translate-y-1/2 text-center"
                  style={{ top: coord.top, left: coord.left }}
                >
                  <div className={`mx-auto h-4 w-4 rounded-full ring-4 ring-white/70 shadow-[0_0_0_10px_rgba(255,255,255,0.12)] ${intensityClass(zone.severity)}`} />
                  <p className="mt-2 text-xs font-semibold">{humanizeSlug(zone.zone)}</p>
                  <p className="text-[11px] text-ink/55">{zone.count} incidents</p>
                </div>
              );
            })
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-ink/55">No current disruptions to map.</div>
          )}
        </div>
        <div className="space-y-3">
          {zoneSummary.length ? (
            zoneSummary.map((zone) => (
              <div key={zone.zone} className="rounded-2xl bg-black/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold">{humanizeSlug(zone.zone)}</p>
                  <span className={`pill text-white ${intensityClass(zone.severity)}`}>Severity {zone.severity.toFixed(2)}</span>
                </div>
                <p className="mt-2 text-sm text-ink/65">{zone.triggers.map(humanizeSlug).join(", ")}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-ink/55">No disruption evidence available in the current time window.</p>
          )}
        </div>
      </div>
    </div>
  );
}
