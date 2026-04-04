"""
Decision engine for routing claims to approve, delay, or reject.
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from backend.utils.time import utc_now_naive


class DecisionEngine:
    WEIGHTS = {"disruption": 0.35, "confidence": 0.25, "fraud_inverse": 0.30, "trust": 0.10}
    THRESHOLDS = {"approved": 0.65, "delayed": 0.45}
    LOW_RISK_REVIEW_FLAGS = {"movement", "pre_activity"}
    MODERATE_REVIEW_FLAGS = {"device"}
    STRONG_REVIEW_FLAGS = {"duplicate", "cluster", "timing", "income_inflation"}

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, float(value)))

    def _decision_margin(self, final_score: float, decision: str, auto_approve: bool, auto_reject: bool) -> float:
        if auto_approve:
            return 0.92
        if auto_reject:
            return 0.92
        if decision == "approved":
            return self._clamp((final_score - self.THRESHOLDS["approved"]) / 0.18)
        if decision == "rejected":
            return self._clamp((self.THRESHOLDS["delayed"] - final_score) / 0.18)
        midpoint = (self.THRESHOLDS["approved"] + self.THRESHOLDS["delayed"]) / 2
        band_half_width = (self.THRESHOLDS["approved"] - self.THRESHOLDS["delayed"]) / 2
        return self._clamp(1 - abs(final_score - midpoint) / max(0.01, band_half_width))

    def _confidence_band(self, value: float) -> str:
        if value >= 0.72:
            return "high"
        if value >= 0.48:
            return "moderate"
        return "low"

    def _primary_reason(self, fraud_flags: list[str], trust_score: float, event_confidence: float, adjusted_fraud: float) -> str:
        if "timing" in fraud_flags:
            return "policy timing risk"
        if "duplicate" in fraud_flags:
            return "duplicate claim pressure"
        if "cluster" in fraud_flags:
            return "cluster fraud pressure"
        if trust_score <= 0.2:
            return "worker trust score"
        if adjusted_fraud >= 0.45:
            return "elevated fraud pressure"
        if "movement" in fraud_flags:
            return "movement anomaly"
        if "pre_activity" in fraud_flags:
            return "weak pre-event activity"
        if event_confidence <= 0.75:
            return "event confidence"
        return "signal alignment requires review"

    def _flag_signal_value(self, fraud_result: Dict[str, Any], flag: str) -> float:
        signals = fraud_result.get("signals")
        if isinstance(signals, dict):
            return self._clamp(signals.get(flag, 0.0))
        if flag in (fraud_result.get("flags") or []):
            return 0.65
        return 0.0

    def _flag_profile(self, fraud_result: Dict[str, Any]) -> Dict[str, Any]:
        fraud_flags = list(fraud_result.get("flags") or [])
        weak_count = 0
        moderate_count = 0
        strong_count = 0
        penalty = 0.0

        for flag in fraud_flags:
            signal_value = self._flag_signal_value(fraud_result, flag)
            if flag in self.STRONG_REVIEW_FLAGS:
                strong_count += 1
                penalty += 0.065 * max(0.5, signal_value)
            elif flag in self.MODERATE_REVIEW_FLAGS:
                moderate_count += 1
                penalty += 0.04 * max(0.4, signal_value)
            else:
                weak_count += 1
                penalty += 0.022 * max(0.35, signal_value)

        if strong_count >= 2:
            penalty += 0.03
        if strong_count == 0 and moderate_count == 0 and weak_count:
            penalty = max(0.0, penalty - 0.015)

        return {
            "weak_count": weak_count,
            "moderate_count": moderate_count,
            "strong_count": strong_count,
            "penalty": round(min(0.18, penalty), 4),
            "noise_only": strong_count == 0 and moderate_count == 0 and weak_count > 0,
        }

    def _automation_confidence(
        self,
        *,
        disruption_score: float,
        event_confidence: float,
        fraud_result: Dict[str, Any],
        trust_score: float,
        feedback_result: Dict[str, Any],
        flag_profile: Dict[str, Any],
    ) -> float:
        signal_agreement = self._clamp(1 - abs(disruption_score - event_confidence))
        model_confidence = fraud_result.get("ml_confidence")
        if model_confidence is None:
            model_confidence = 0.38 if fraud_result.get("fallback_used") else 0.62
        model_confidence = self._clamp(model_confidence)
        data_completeness = 1.0 if fraud_result.get("raw_fraud_score") is not None else 0.7
        fraud_safety = self._clamp(1 - float(fraud_result.get("adjusted_fraud_score", 0.0)))
        feedback_strength = self._clamp(
            abs(float(feedback_result.get("score_adjustment", 0.0))) * 8
            + float(feedback_result.get("confidence", 0.0)) * 0.4
        )
        flag_penalty = min(0.12, float(flag_profile.get("penalty", 0.0)) * 1.3)
        confidence = (
            (0.28 * signal_agreement)
            + (0.22 * model_confidence)
            + (0.18 * data_completeness)
            + (0.18 * self._clamp(trust_score))
            + (0.14 * fraud_safety)
            + (0.04 * feedback_strength)
            - flag_penalty
        )
        return round(self._clamp(confidence), 3)

    def _decision_confidence(
        self,
        *,
        final_score: float,
        decision: str,
        disruption_score: float,
        event_confidence: float,
        fraud_result: Dict[str, Any],
        trust_score: float,
        fraud_flags: list[str],
        flag_profile: Dict[str, Any],
        auto_approve: bool,
        auto_reject: bool,
        feedback_result: Dict[str, Any],
    ) -> float:
        signal_agreement = self._clamp(1 - abs(disruption_score - event_confidence))
        model_confidence = fraud_result.get("ml_confidence")
        if model_confidence is None:
            model_confidence = 0.38 if fraud_result.get("fallback_used") else 0.62
        model_confidence = self._clamp(model_confidence)
        data_completeness = 1.0 if fraud_result.get("raw_fraud_score") is not None else 0.7
        decision_margin = self._decision_margin(final_score, decision, auto_approve, auto_reject)
        trust_alignment = trust_score if decision != "rejected" else 1 - trust_score
        feedback_strength = self._clamp(
            abs(float(feedback_result.get("score_adjustment", 0.0))) * 8
            + float(feedback_result.get("confidence", 0.0)) * 0.4
        )
        flag_penalty = min(0.14, float(flag_profile.get("penalty", 0.0)) * 1.6)

        confidence = (
            (0.34 * decision_margin)
            + (0.24 * signal_agreement)
            + (0.18 * model_confidence)
            + (0.12 * data_completeness)
            + (0.08 * self._clamp(trust_alignment))
            + (0.04 * feedback_strength)
            - flag_penalty
        )
        return round(self._clamp(confidence), 3)

    def decide(
        self,
        disruption_score: float,
        event_confidence: float,
        fraud_result: Dict,
        trust_score: float,
        feedback_result: Dict[str, Any] | None = None,
        payout_amount: float | None = None,
    ) -> Dict:
        feedback_result = feedback_result or {}
        adjusted_fraud = fraud_result["adjusted_fraud_score"]
        fraud_flags = fraud_result["flags"]
        flag_profile = self._flag_profile(fraud_result)
        payout_amount = max(0.0, float(payout_amount or 0.0))
        disruption_component = self.WEIGHTS["disruption"] * disruption_score
        confidence_component = self.WEIGHTS["confidence"] * event_confidence
        fraud_component = self.WEIGHTS["fraud_inverse"] * (1 - adjusted_fraud)
        trust_component = self.WEIGHTS["trust"] * trust_score
        flag_penalty = float(flag_profile["penalty"])
        if adjusted_fraud >= 0.70:
            flag_penalty = max(flag_penalty, 0.15)
        feedback_adjustment = max(-0.08, min(0.08, float(feedback_result.get("score_adjustment", 0.0))))
        base_final_score = min(
            1.0,
            max(0.0, disruption_component + confidence_component + fraud_component + trust_component - flag_penalty),
        )

        final_score = round(
            min(1.0, max(0.0, base_final_score + feedback_adjustment)),
            3,
        )

        auto_approve = (
            adjusted_fraud <= 0.18
            and trust_score >= 0.09
            and event_confidence >= 0.75
            and disruption_score >= 0.65
        )
        trusted_low_risk_approve = (
            adjusted_fraud <= 0.18
            and trust_score >= 0.20
            and event_confidence >= 0.70
            and final_score >= 0.55
            and set(fraud_flags).issubset(self.LOW_RISK_REVIEW_FLAGS)
        )
        auto_reject = (
            adjusted_fraud >= 0.55
            and len(fraud_flags) >= 3
            and trust_score <= 0.35
        )
        automation_confidence = self._automation_confidence(
            disruption_score=disruption_score,
            event_confidence=event_confidence,
            fraud_result=fraud_result,
            trust_score=trust_score,
            feedback_result=feedback_result,
            flag_profile=flag_profile,
        )
        low_payout_confident_approve = (
            payout_amount <= 100
            and adjusted_fraud <= 0.30
            and trust_score >= 0.09
            and event_confidence >= 0.70
            and final_score >= 0.55
            and automation_confidence >= 0.60
            and flag_profile["strong_count"] == 0
        )
        weak_signal_confident_approve = (
            flag_profile["noise_only"]
            and adjusted_fraud <= 0.24
            and trust_score >= 0.09
            and event_confidence >= 0.70
            and final_score >= 0.55
            and automation_confidence >= 0.55
            and payout_amount <= 140
        )
        threshold_score_approve = final_score >= self.THRESHOLDS["approved"] and (
            final_score >= 0.78 or automation_confidence >= 0.56
        )

        if (
            auto_approve
            or trusted_low_risk_approve
            or weak_signal_confident_approve
            or low_payout_confident_approve
            or threshold_score_approve
        ):
            decision = "approved"
            if auto_approve:
                explanation = f"Claim auto-approved by strong signal alignment (score: {final_score})."
            elif trusted_low_risk_approve:
                explanation = (
                    f"Claim approved for trusted low-fraud profile despite mild review signals (score: {final_score})."
                )
            elif weak_signal_confident_approve:
                explanation = (
                    f"Claim approved because only weak review signals were present and confidence stayed stable (score: {final_score})."
                )
            elif low_payout_confident_approve:
                explanation = (
                    f"Claim approved because payout exposure stayed low and confidence remained stable (score: {final_score})."
                )
            else:
                explanation = f"Claim approved with sufficient confidence (score: {final_score})."
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

        decision_confidence = self._decision_confidence(
            final_score=final_score,
            decision=decision,
            disruption_score=disruption_score,
            event_confidence=event_confidence,
            fraud_result=fraud_result,
            trust_score=trust_score,
            fraud_flags=fraud_flags,
            flag_profile=flag_profile,
            auto_approve=(
                auto_approve
                or trusted_low_risk_approve
                or weak_signal_confident_approve
                or low_payout_confident_approve
            ),
            auto_reject=auto_reject,
            feedback_result=feedback_result,
        )
        primary_reason = self._primary_reason(fraud_flags, trust_score, event_confidence, adjusted_fraud)

        return {
            "final_score": final_score,
            "decision": decision,
            "explanation": explanation,
            "decision_confidence": decision_confidence,
            "decision_confidence_band": self._confidence_band(decision_confidence),
            "primary_reason": primary_reason,
            "breakdown": {
                "disruption_component": round(disruption_component, 4),
                "confidence_component": round(confidence_component, 4),
                "fraud_component": round(fraud_component, 4),
                "trust_component": round(trust_component, 4),
                "flag_penalty": round(flag_penalty, 4),
                "weak_flag_count": flag_profile["weak_count"],
                "moderate_flag_count": flag_profile["moderate_count"],
                "strong_flag_count": flag_profile["strong_count"],
                "feedback_adjustment": round(feedback_adjustment, 4),
                "base_final_score": round(base_final_score, 4),
                "automation_confidence": automation_confidence,
                "weights": self.WEIGHTS,
            },
            "inputs": {
                "disruption_score": disruption_score,
                "event_confidence": event_confidence,
                "adjusted_fraud_score": adjusted_fraud,
                "raw_fraud_score": fraud_result["raw_fraud_score"],
                "trust_score": trust_score,
                "fraud_flags": fraud_flags,
                "payout_amount": payout_amount,
                "weak_signal_confident_approve": weak_signal_confident_approve,
                "low_payout_confident_approve": low_payout_confident_approve,
                "auto_approve": auto_approve,
                "trusted_low_risk_approve": trusted_low_risk_approve,
                "auto_reject": auto_reject,
                "feedback_result": feedback_result,
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
