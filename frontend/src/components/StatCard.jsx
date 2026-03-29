export default function StatCard({ label, value, hint, tone = "ink" }) {
  const toneMap = {
    ink: "from-white to-white",
    storm: "from-storm/10 to-white",
    forest: "from-forest/10 to-white",
    ember: "from-ember/10 to-white",
    gold: "from-gold/15 to-white",
  };

  return (
    <div className={`panel bg-gradient-to-br ${toneMap[tone] || toneMap.ink} p-5`}>
      <p className="text-sm text-ink/55">{label}</p>
      <p className="mt-3 text-3xl font-bold">{value}</p>
      {hint ? <p className="mt-2 text-sm text-ink/60">{hint}</p> : null}
    </div>
  );
}
