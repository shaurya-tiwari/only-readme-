export default function TrustScoreGauge({ score = 0 }) {
  const numeric = Number(score || 0);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const progress = circumference - circumference * Math.max(0, Math.min(1, numeric));

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-28 w-28">
        <svg className="h-28 w-28 -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={radius} stroke="#e2e3e0" strokeWidth="10" fill="none" />
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke="#003535"
            strokeWidth="10"
            strokeLinecap="round"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={progress}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-primary">{numeric.toFixed(2)}</span>
          <span className="text-[11px] uppercase tracking-[0.24em] text-on-surface-variant">Trust</span>
        </div>
      </div>
      <div className="space-y-2 text-sm text-on-surface-variant">
        <p><span className="font-semibold text-primary">Risk:</span> Zone and earnings context</p>
        <p><span className="font-semibold text-primary">Fraud:</span> Used to protect payout integrity</p>
        <p><span className="font-semibold text-primary">Trust:</span> Stabilizes borderline decisions</p>
      </div>
    </div>
  );
}
