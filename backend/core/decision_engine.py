"""
Decision engine for routing claims to approve, delay, or reject.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DecisionEngine:
    WEIGHTS = {"disruption": 0.35, "confidence": 0.25, "fraud_inverse": 0.25, "trust": 0.15}
    THRESHOLDS = {"approved": 0.70, "delayed": 0.50}

    def decide(self, disruption_score: float, event_confidence: float, fraud_result: Dict, trust_score: float) -> Dict:
        adjusted_fraud = fraud_result["adjusted_fraud_score"]
        fraud_flags = fraud_result["flags"]
        disruption_component = self.WEIGHTS["disruption"] * disruption_score
        confidence_component = self.WEIGHTS["confidence"] * event_confidence
        fraud_component = self.WEIGHTS["fraud_inverse"] * (1 - adjusted_fraud)
        trust_component = self.WEIGHTS["trust"] * trust_score
        flag_penalty = min(0.16, max(0, len(fraud_flags) - 1) * 0.04)
        if adjusted_fraud >= 0.70:
            flag_penalty = max(flag_penalty, 0.15)

        final_score = round(
            min(1.0, max(0.0, disruption_component + confidence_component + fraud_component + trust_component - flag_penalty)),
            3,
        )

        auto_approve = (
            adjusted_fraud <= 0.18
            and trust_score >= 0.55
            and event_confidence >= 0.8
            and disruption_score >= 0.68
        )
        auto_reject = (
            adjusted_fraud >= 0.55
            and len(fraud_flags) >= 3
            and trust_score <= 0.35
        )

        if auto_approve or final_score >= self.THRESHOLDS["approved"]:
            decision = "approved"
            explanation = (
                f"Claim approved with high confidence (score: {final_score})."
                if not auto_approve
                else f"Claim auto-approved by strong signal alignment (score: {final_score})."
            )
        elif auto_reject or final_score < self.THRESHOLDS["delayed"]:
            decision = "rejected"
            explanation = (
                f"Claim rejected (score: {final_score})."
                if not auto_reject
                else f"Claim rejected by high fraud pressure and low trust (score: {final_score})."
            )
        else:
            decision = "delayed"
            explanation = f"Claim delayed for manual review (score: {final_score})."

        return {
            "final_score": final_score,
            "decision": decision,
            "explanation": explanation,
            "breakdown": {
                "disruption_component": round(disruption_component, 4),
                "confidence_component": round(confidence_component, 4),
                "fraud_component": round(fraud_component, 4),
                "trust_component": round(trust_component, 4),
                "flag_penalty": round(flag_penalty, 4),
                "weights": self.WEIGHTS,
            },
            "inputs": {
                "disruption_score": disruption_score,
                "event_confidence": event_confidence,
                "adjusted_fraud_score": adjusted_fraud,
                "raw_fraud_score": fraud_result["raw_fraud_score"],
                "trust_score": trust_score,
                "fraud_flags": fraud_flags,
                "auto_approve": auto_approve,
                "auto_reject": auto_reject,
            },
            "review_deadline": utc_now_naive() + timedelta(hours=24) if decision == "delayed" else None,
        }

    def estimate_disruption_hours(self, event_started_at: datetime, severity: float) -> float:
        if severity > 1.5:
            base_hours = 4.0
        elif severity > 1.0:
            base_hours = 3.0
        elif severity > 0.5:
            base_hours = 2.0
        else:
            base_hours = 1.0
        elapsed = (utc_now_naive() - event_started_at).total_seconds() / 3600
        return round(min(base_hours, max(1.0, elapsed)), 1)


decision_engine = DecisionEngine()
