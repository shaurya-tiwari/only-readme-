import { formatCurrency, formatDateTime, formatScore, humanizeSlug, statusPill } from "../utils/formatters";
import { patternCopy, workerClaimNarrative, workerFriendlyFactors } from "../utils/decisionNarrative";
import { t } from "../utils/i18n";
import WhatsAppPreview from "./WhatsAppPreview";

function renderTriggerList(triggers = []) {
  if (!triggers.length) {
    return "None";
  }
  return triggers.map(humanizeSlug).join(", ");
}

export default function ClaimDetailPanel({ claim }) {
  if (!claim) {
    return (
      <div className="context-panel p-6">
        <div className="mb-5">
          <p className="eyebrow">Claim detail</p>
          <h3 className="mt-2 text-2xl font-bold text-primary">{t("claim.select")}</h3>
        </div>
        <p className="text-sm leading-6 text-on-surface-variant">
          {t("claim.pick")}
        </p>
      </div>
    );
  }

  const breakdown = claim.decision_breakdown || {};
  const inputs = breakdown.inputs || {};
  const components = breakdown.breakdown || {};
  const payoutBreakdown = claim.payout_breakdown || breakdown.payout_breakdown || {};
  const fraudModel = claim.fraud_model || breakdown.fraud_model || {};
  const incidentTriggers = inputs.incident_triggers || claim.decision_breakdown?.incident_triggers || [claim.trigger_type];
  const coveredTriggers = inputs.covered_triggers || claim.decision_breakdown?.covered_triggers || [];
  const pattern = components.pattern_taxonomy;
  const patternNarrative = patternCopy(pattern);
  const workerFactors = workerFriendlyFactors(claim);
  const decisionExperience = claim.decision_experience || {};
  const behaviorLabel = decisionExperience.behavioral_label ? humanizeSlug(decisionExperience.behavioral_label) : null;

  return (
    <div className="context-panel p-6">
      <div className="mb-5">
        <p className="eyebrow">Claim detail</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className={statusPill(claim.status)}>{humanizeSlug(claim.status)}</span>
          <h3 className="text-2xl font-bold text-primary">{renderTriggerList(incidentTriggers)}</h3>
        </div>
        <p className="mt-2 text-sm text-on-surface-variant">{formatDateTime(claim.created_at)}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-on-surface-variant">Decision explanation</p>
          <p className="mt-3 text-sm leading-7 text-on-surface">
            {decisionExperience.summary || breakdown.explanation || claim.rejection_reason || "No explanation available."}
          </p>
          {decisionExperience.action_reason ? (
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">{decisionExperience.action_reason}</p>
          ) : null}
          {decisionExperience.next_step ? (
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">Next step: {decisionExperience.next_step}</p>
          ) : null}
        </div>
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-on-surface-variant">Payout impact</p>
          <p className="mt-3 text-lg font-semibold text-primary">
            {formatCurrency(claim.final_payout || claim.calculated_payout)}
          </p>
          <p className="mt-3 text-sm leading-6 text-on-surface-variant">
            Hours affected: {claim.disruption_hours ?? "--"} - Peak multiplier: {claim.peak_multiplier ?? "--"}
          </p>
          {payoutBreakdown.net_income_per_hour ? (
            <div className="mt-4 space-y-1 text-sm leading-6 text-on-surface-variant">
              <p>Gross hourly reference: {formatCurrency(payoutBreakdown.income_per_hour)}</p>
              <p>Net protected hourly: {formatCurrency(payoutBreakdown.net_income_per_hour)}</p>
              <p>
                Operating-cost factor: {Math.round(Number(payoutBreakdown.operating_cost_factor || 0) * 100)}%
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {/* Income Protection — the core value proposition */}
      {claim.income_loss && claim.income_loss.estimated_income_loss > 0 ? (
        <div className="mt-4 panel-quiet rounded-[24px] p-4" style={{ borderLeft: '4px solid var(--primary)' }}>
          <p className="eyebrow" style={{ fontSize: '0.75rem', letterSpacing: '0.08em', color: 'var(--on-surface-variant)' }}>
            Income Protection Summary
          </p>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-sm text-on-surface-variant">{t("claim.income_loss")}</p>
              <p className="mt-1 text-lg font-bold" style={{ color: '#ef5350' }}>
                {formatCurrency(claim.income_loss.estimated_income_loss)}
              </p>
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">{t("claim.coverage")}</p>
              <p className="mt-1 text-lg font-bold" style={{ color: '#66bb6a' }}>
                {formatCurrency(claim.income_loss.payout_amount)}
              </p>
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Coverage</p>
              <p className="mt-1 text-lg font-bold text-primary">
                {Math.round(claim.income_loss.coverage_ratio * 100)}%
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-on-surface-variant">
            Based on {formatCurrency(claim.income_loss.calculation_basis?.income_per_hour)}/hr
            × {claim.income_loss.calculation_basis?.disruption_hours}h disruption
            {claim.income_loss.calculation_basis?.peak_multiplier > 1 ? ` × ${claim.income_loss.calculation_basis.peak_multiplier}x peak` : ''}
          </p>
        </div>
      ) : null}

      <WhatsAppPreview claim={claim} />

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-sm text-on-surface-variant">Decision strength</p>
          <p className="mt-2 font-semibold text-primary">{formatScore(claim.final_score)}</p>
        </div>
        <div>
          <p className="text-sm text-on-surface-variant">Payment safety check</p>
          <p className="mt-2 font-semibold text-primary">{formatScore(claim.fraud_score)}</p>
        </div>
        <div>
          <p className="text-sm text-on-surface-variant">Incident evidence</p>
          <p className="mt-2 font-semibold text-primary">{formatScore(claim.event_confidence)}</p>
        </div>
        <div>
          <p className="text-sm text-on-surface-variant">Account trust</p>
          <p className="mt-2 font-semibold text-primary">{formatScore(claim.trust_score)}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-on-surface-variant">Claim checks</p>
          <p className="mt-2 text-lg font-semibold text-primary">
            {fraudModel.fraud_probability !== undefined
              ? `${Math.round(Number(fraudModel.fraud_probability || 0) * 100)}% check intensity`
              : "Standard automated checks"}
          </p>
          {behaviorLabel ? <p className="mt-3 text-sm leading-6 text-on-surface-variant">Case type: {behaviorLabel}</p> : null}
          {Array.isArray(fraudModel.top_factors) && fraudModel.top_factors.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {workerFactors.map((factor) => (
                <span key={factor} className="pill" style={{ background: "rgba(120,53,0,0.3)", color: "#f4a135" }}>
                  {factor}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">No elevated review checks on this claim.</p>
          )}
        </div>
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-on-surface-variant">Worker explanation</p>
          <p className="mt-2 text-sm leading-7 text-on-surface">
            {workerClaimNarrative(claim)}
          </p>
          {decisionExperience.confidence_note ? (
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">{decisionExperience.confidence_note}</p>
          ) : null}
          {behaviorLabel ? (
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">
              Claim pattern: <span className="font-semibold text-primary">{behaviorLabel}</span>
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-on-surface-variant">Incident triggers</p>
          <p className="mt-2 text-sm leading-7 text-on-surface">{renderTriggerList(incidentTriggers)}</p>
          <p className="mt-3 text-sm text-on-surface-variant">Covered by policy</p>
          <p className="mt-2 text-sm leading-7 text-on-surface">{renderTriggerList(coveredTriggers)}</p>
        </div>
        <div className="panel-quiet rounded-[24px] p-4">
          <p className="text-sm text-on-surface-variant">AI Decision Factors</p>
          <div className="mt-3 space-y-3">
            {[
              { label: "Disruption strength", value: components.disruption_component, color: "#42a5f5" },
              { label: "Incident evidence", value: components.confidence_component, color: "#66bb6a" },
              { label: "Payment safety", value: components.fraud_component, color: "#ef5350" },
              { label: "Account trust", value: components.trust_component, color: "#ab47bc" },
              { label: "Flag penalty", value: components.flag_penalty, color: "#ffa726" },
            ].map(({ label, value, color }) => {
              const pct = Math.round(Math.max(0, Math.min(1, Number(value || 0))) * 100);
              return (
                <div key={label}>
                  <div className="flex items-center justify-between text-xs text-on-surface-variant mb-1">
                    <span>{label}</span>
                    <span className="font-semibold text-on-surface">{formatScore(value)}</span>
                  </div>
                  <div style={{ width: "100%", height: "6px", borderRadius: "3px", background: "rgba(255,255,255,0.08)" }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        height: "6px",
                        borderRadius: "3px",
                        background: color,
                        transition: "width 0.6s ease",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          {fraudModel.confidence !== undefined ? (
            <p className="mt-4 text-xs text-on-surface-variant">
              Model confidence: <span className="font-semibold text-on-surface">{Math.round(Number(fraudModel.confidence || 0) * 100)}%</span>
              {fraudModel.model_version ? ` · v${fraudModel.model_version}` : ""}
              {fraudModel.fallback_used ? " · fallback mode" : ""}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
