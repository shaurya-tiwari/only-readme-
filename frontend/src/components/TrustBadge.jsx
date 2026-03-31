export default function TrustBadge({ score }) {
  const numeric = Number(score || 0);
  const label = numeric >= 0.7 ? "High trust" : numeric >= 0.4 ? "Medium trust" : "Building trust";
  const tone = numeric >= 0.7 ? "bg-emerald-100 text-emerald-800" : numeric >= 0.4 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-800";

  return <span className={`pill ${tone}`}>{label}: {numeric.toFixed(2)}</span>;
}
