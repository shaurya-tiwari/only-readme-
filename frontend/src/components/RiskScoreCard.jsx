import { useEffect, useMemo, useState } from "react";
import { AlertCircle, TrendingUp } from "lucide-react";

import { workersApi } from "../api/workers";
import { humanizeSlug } from "../utils/formatters";

export default function RiskScoreCard({ workerId }) {
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!workerId) {
      setLoading(false);
      return;
    }

    const loadRisk = async () => {
      try {
        setLoading(true);
        const res = await workersApi.risk(workerId);
        setRiskData(res.data);
        setError(null);
      } catch (err) {
        setError(err.message || "Failed to load risk score");
        console.error("Risk score load error:", err);
      } finally {
        setLoading(false);
      }
    };

    loadRisk();
  }, [workerId]);

  const breakdown = riskData?.breakdown || {};
  const rawScore = Number(riskData?.risk_score);
  const score = Number.isFinite(rawScore) ? rawScore : 0;
  const scorePercent = Math.round(score * 100);
  const topFactors = useMemo(() => {
    const rawFactors = Array.isArray(breakdown.top_factors) ? breakdown.top_factors : [];
    return rawFactors
      .map((factor, index) => {
        const rawContribution =
          factor?.contribution ??
          factor?.weight ??
          factor?.impact ??
          factor?.score ??
          factor?.value ??
          0;
        const contribution = Number(rawContribution);
        return {
          id: factor?.factor || factor?.name || `factor-${index}`,
          label: humanizeSlug(factor?.factor || factor?.name || "factor"),
          contribution: Number.isFinite(contribution) ? contribution : 0,
        };
      })
      .filter((factor) => factor.contribution > 0);
  }, [breakdown.top_factors]);

  if (loading) {
    return (
      <div className="panel p-6">
        <p className="eyebrow">Coverage outlook</p>
        <p className="mt-4 text-sm text-on-surface-variant">Loading...</p>
      </div>
    );
  }

  if (error || !riskData) {
    return (
      <div className="panel p-6">
        <p className="eyebrow">Coverage outlook</p>
        <p className="mt-4 text-sm text-on-surface-variant">{error || "No risk data available"}</p>
      </div>
    );
  }

  const riskLevel = breakdown.risk_level || "unknown";
  const riskColor =
    {
      low:      { style: { background: "rgba(0,53,48,0.4)", color: "#69f8e9" },       dot: "bg-emerald-400" },
      moderate: { style: { background: "rgba(71,35,190,0.25)", color: "#cabeff" },    dot: "bg-violet-400" },
      elevated: { style: { background: "rgba(120,53,0,0.3)", color: "#f4a135" },      dot: "bg-amber-400" },
      high:     { style: { background: "rgba(147,0,10,0.25)", color: "#ffb4ab" },     dot: "bg-red-400" },
    }[riskLevel] || { style: { background: "rgba(34,42,61,0.6)", color: "#c6c5d1" }, dot: "bg-slate-400" };
  const authorityClass =
    riskLevel === "high"
      ? "card-primary border-accent-left border-accent-error"
      : riskLevel === "elevated" || riskLevel === "moderate"
        ? "card-primary border-accent-left border-accent-warning"
        : "card-primary border-accent-left border-accent-success";
  const explanation =
    breakdown.explanation ||
    "Coverage outlook is based on location, disruption pressure, and incident context in the worker's operating zone.";

  return (
    <div className={`panel p-6 ${authorityClass}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Coverage outlook</p>
          <p className="mt-4 text-5xl font-extrabold leading-none text-primary">{scorePercent}%</p>
          <p className="mt-2 text-sm font-medium text-on-surface-variant">Current disruption outlook</p>
        </div>
        <span className="pill" style={riskColor.style}>
          <span className={`mr-2 inline-block h-2 w-2 rounded-full ${riskColor.dot}`} />
          {riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)}
        </span>
      </div>

      <div className="mt-5 panel-quiet rounded-[24px] p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">Why this matters now</p>
        <p className="mt-3 text-sm leading-6 text-on-surface">{explanation}</p>
      </div>

      {topFactors.length ? (
        <div className="mt-5 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">Main signals</p>
          <div className="space-y-2">
            {topFactors.slice(0, 3).map((factor) => (
              <div key={factor.id} className="flex items-center justify-between gap-4 rounded-[16px] bg-surface-container-low p-3 text-sm">
                <span className="text-on-surface-variant">{factor.label}</span>
                <span className="font-semibold text-primary">
                  {(() => {
                    const c = Number(factor.contribution);
                    const safe = Number.isFinite(c) ? c : 0;
                    return `${(safe * 100).toFixed(1)}%`;
                  })()}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-5 flex items-start gap-2 rounded-[16px] bg-surface-container-low p-3 text-xs leading-5 text-on-surface-variant">
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>Detailed signal contributions are not available for this view yet.</span>
        </div>
      )}
      <div className="mt-5 flex items-center gap-2 rounded-[16px] bg-surface-container-low p-3">
        <TrendingUp size={14} className="text-on-surface-variant" />
        <div className="text-xs text-on-surface-variant">
          RideShield keeps tracking this outlook as new disruption signals arrive.
        </div>
      </div>
    </div>
  );
}
