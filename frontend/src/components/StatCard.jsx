export default function StatCard({ label, value, hint, tone = "ink" }) {
  const toneMap = {
    ink: "from-white to-[#fcfcfa]",
    storm: "from-[#dfe9f4] to-white",
    forest: "from-[#dff0e6] to-white",
    ember: "from-[#f6e4dc] to-white",
    gold: "from-[#f6ecd6] to-white",
  };

  return (
    <div className={`metric-card bg-gradient-to-br ${toneMap[tone] || toneMap.ink}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-ink/45">{label}</p>
      <p className="mt-4 text-3xl font-bold text-[#173126] sm:text-[2rem]">{value}</p>
      {hint ? <p className="mt-3 max-w-[18rem] text-sm leading-6 text-ink/60">{hint}</p> : null}
    </div>
  );
}
