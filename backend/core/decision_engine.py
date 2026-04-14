"""
Decision engine for routing claims to approve, delay, or reject.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict
from backend.config import settings
from backend.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    layer: str
    decision: str
    explanation_template: str
    purpose: str
    surface: str
    risk_expectation: str
    matcher: Callable[[dict[str, Any]], bool]


class DecisionEngine:
    POLICY_VERSION = settings.DECISION_POLICY_VERSION
    POLICY_LAYERS = (
        "fraud_layer",
        "strong_approve_layer",
        "micro_payout_safe_lane",
        "ambiguity_resolver",
        "review_fallback",
    )
    WEIGHTS = {"disruption": 0.35, "confidence": 0.25, "fraud_inverse": 0.30, "trust": 0.10}
    THRESHOLDS = {
        "approved": settings.DECISION_APPROVED_THRESHOLD,
        "borderline_approved": settings.DECISION_BORDERLINE_APPROVED_THRESHOLD,
        "delayed": settings.DECISION_DELAYED_THRESHOLD,
    }
    PAYOUT_CAPS = {
        "low_payout_confident": settings.DECISION_LOW_PAYOUT_CONFIDENT_CAP,
        "weak_signal_confident": settings.DECISION_WEAK_SIGNAL_CONFIDENT_CAP,
        "borderline_confident": settings.DECISION_BORDERLINE_CONFIDENT_CAP,
        "false_review_safe_lane": settings.DECISION_FALSE_REVIEW_PAYOUT_CAP,
        "device_micro_payout": settings.DECISION_DEVICE_MICRO_PAYOUT_CAP,
        "cluster_micro_payout": settings.DECISION_CLUSTER_MICRO_PAYOUT_CAP,
    }
    FALSE_REVIEW_SCORE_FLOOR = settings.DECISION_FALSE_REVIEW_SCORE_FLOOR
    LOW_RISK_REVIEW_FLAGS = {"movement", "pre_activity"}
    MODERATE_REVIEW_FLAGS = {"device"}
    STRONG_REVIEW_FLAGS = {"duplicate", "timing", "income_inflation"}
    HIGH_CONFIDENCE_THRESHOLD = settings.DECISION_HIGH_CONFIDENCE_THRESHOLD
    MODERATE_CONFIDENCE_THRESHOLD = settings.DECISION_MODERATE_CONFIDENCE_THRESHOLD
    GUARDRAILS = {
        "low_payout": settings.DECISION_LOW_PAYOUT_THRESHOLD,
        "high_payout": settings.DECISION_HIGH_PAYOUT_THRESHOLD,
        "high_trust": settings.DECISION_HIGH_TRUST_THRESHOLD,
        "low_confidence": settings.DECISION_LOW_CONFIDENCE_THRESHOLD,
        "gray_band_low": settings.DECISION_GRAY_BAND_LOW,
        "gray_band_high": settings.DECISION_GRAY_BAND_HIGH,
    }
    REASON_LIMIT = settings.DECISION_REASON_LIMIT

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
        if value >= self.HIGH_CONFIDENCE_THRESHOLD:
            return "high"
        if value >= self.MODERATE_CONFIDENCE_THRESHOLD:
            return "moderate"
        return "low"

    def _primary_reason(self, fraud_flags: list[str], trust_score: float, event_confidence: float, adjusted_fraud: float) -> str:
        return self._reason_labels(
            fraud_flags=fraud_flags,
            trust_score=trust_score,
            event_confidence=event_confidence,
            adjusted_fraud=adjusted_fraud,
        )[0]

    def _reason_labels(
        self,
        *,
        fraud_flags: list[str],
        trust_score: float,
        event_confidence: float,
        adjusted_fraud: float,
    ) -> list[str]:
        ordered_reasons: list[str] = []

        def add_reason(value: str) -> None:
            if value not in ordered_reasons:
                ordered_reasons.append(value)

        if "timing" in fraud_flags:
            add_reason("policy timing risk")
        if "duplicate" in fraud_flags:
            add_reason("duplicate claim pressure")
        if "cluster" in fraud_flags:
            add_reason("cluster fraud pressure")
        if "income_inflation" in fraud_flags:
            add_reason("income inflation pressure")
        if trust_score <= 0.2:
            add_reason("worker trust score")
        if adjusted_fraud >= 0.45:
            add_reason("elevated fraud pressure")
        if "movement" in fraud_flags:
            add_reason("movement anomaly")
        if "pre_activity" in fraud_flags:
            add_reason("weak pre-event activity")
        if "device" in fraud_flags:
            add_reason("device risk")
        if event_confidence <= 0.75:
            add_reason("event confidence")
        if not ordered_reasons:
            add_reason("signal alignment requires review")
        return ordered_reasons[: self.REASON_LIMIT]

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
        cluster_count = 0
        penalty = 0.0

        for flag in fraud_flags:
            signal_value = self._flag_signal_value(fraud_result, flag)
            if flag == "cluster":
                cluster_count += 1
                continue
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
            "cluster_count": cluster_count,
            "penalty": round(min(0.18, penalty), 4),
            "noise_only": strong_count == 0 and moderate_count == 0 and weak_count > 0,
        }

    def _pattern_taxonomy(
        self,
        *,
        fraud_flags: list[str],
        flag_profile: Dict[str, Any],
        payout_amount: float,
        adjusted_fraud: float,
        trust_score: float,
        event_confidence: float,
        automation_confidence: float,
        final_score: float,
    ) -> Dict[str, Any]:
        flag_set = set(fraud_flags)
        if flag_set == {"cluster", "device"} and (
            payout_amount <= self.PAYOUT_CAPS["cluster_micro_payout"]
            and adjusted_fraud <= 0.16
            and trust_score >= 0.28
            and event_confidence >= 0.9
            and automation_confidence >= 0.52
            and final_score >= 0.63
        ):
            return {
                "name": "cluster_micro_resolved",
                "auto_lane": True,
                "manual_bias": "guarded_approve",
            }
        if "cluster" in flag_set and ("device" in flag_set or "pre_activity" in flag_set or "movement" in flag_set):
            return {
                "name": "cluster_combo_pressure",
                "auto_lane": False,
                "manual_bias": "strong_review",
            }
        if flag_set == {"device"} and (
            payout_amount <= self.PAYOUT_CAPS["device_micro_payout"]
            and adjusted_fraud <= 0.12
            and trust_score >= 0.6
            and event_confidence >= 0.45
            and automation_confidence >= 0.45
            and final_score >= self.THRESHOLDS["delayed"]
        ):
            return {
                "name": "device_micro_noise",
                "auto_lane": True,
                "manual_bias": "guarded_approve",
            }
        if flag_set.issubset(self.LOW_RISK_REVIEW_FLAGS) and flag_profile["noise_only"]:
            return {
                "name": "weak_overlap_noise",
                "auto_lane": True,
                "manual_bias": "weak_review",
            }
        if flag_set == {"device"}:
            return {
                "name": "device_watch",
                "auto_lane": False,
                "manual_bias": "moderate_review",
            }
        return {
            "name": "mixed_review_pressure",
            "auto_lane": False,
            "manual_bias": "standard",
        }

    def _classify_cluster_context(
        self,
        *,
        fraud_flags: list[str],
        payout_amount: float,
        adjusted_fraud: float,
        trust_score: float,
        event_confidence: float,
        automation_confidence: float,
        final_score: float,
        flag_profile: Dict[str, Any],
    ) -> dict[str, Any]:
        if "cluster" not in set(fraud_flags):
            return {
                "type": "not_clustered",
                "routing": "none",
                "raw_penalty_active": False,
            }

        if (
            set(fraud_flags) == {"cluster", "device"}
            and payout_amount <= self.PAYOUT_CAPS["cluster_micro_payout"]
            and adjusted_fraud <= 0.16
            and trust_score >= 0.28
            and event_confidence >= 0.9
            and automation_confidence >= 0.52
            and final_score >= 0.63
        ):
            return {
                "type": "coincidence_cluster",
                "routing": "guarded_micro_approve",
                "raw_penalty_active": False,
            }

        if "timing" in fraud_flags or "income_inflation" in fraud_flags or "device" in fraud_flags:
            return {
                "type": "fraud_ring",
                "routing": "strong_review",
                "raw_penalty_active": False,
            }

        if (
            flag_profile["strong_count"] == 1
            and flag_profile["moderate_count"] == 0
            and trust_score >= 0.45
            and event_confidence >= 0.7
        ):
            return {
                "type": "mixed_cluster",
                "routing": "review",
                "raw_penalty_active": False,
            }

        return {
            "type": "mixed_cluster",
            "routing": "review",
            "raw_penalty_active": False,
        }

    def _gray_band_surface(
        self,
        *,
        final_score: float,
        payout_amount: float,
        trust_score: float,
        adjusted_fraud: float,
        fraud_flags: list[str],
        flag_profile: Dict[str, Any],
        uncertainty_case: str | None,
        cluster_context: dict[str, Any],
    ) -> str | None:
        if not (self.GUARDRAILS["gray_band_low"] <= final_score < self.GUARDRAILS["gray_band_high"]):
            return None
        if cluster_context["routing"] != "none":
            return "cluster_sensitive_surface"
        if (
            adjusted_fraud > 0.28
            or flag_profile["moderate_count"] > 0
            or uncertainty_case in {"silent_conflict", "too_perfect_state"}
        ):
            return "early_fraud_signal_surface"
        if trust_score < 0.45:
            return "mid_trust_ambiguity_surface"
        if (
            payout_amount <= self.GUARDRAILS["low_payout"]
            and set(fraud_flags).issubset(self.LOW_RISK_REVIEW_FLAGS)
            and uncertainty_case in {None, "noise_overload"}
        ):
            return "low_payout_legit_surface"
        return "mid_trust_ambiguity_surface"

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

    def _uncertainty_case(
        self,
        *,
        final_score: float,
        disruption_score: float,
        event_confidence: float,
        adjusted_fraud: float,
        trust_score: float,
        flag_profile: Dict[str, Any],
        automation_confidence: float,
    ) -> str | None:
        signal_agreement_gap = abs(disruption_score - event_confidence)

        if disruption_score >= 0.7 and event_confidence >= 0.7 and adjusted_fraud >= 0.35 and trust_score <= 0.25:
            return "core_contradiction"
        if final_score >= 0.65 and adjusted_fraud <= 0.1 and trust_score >= 0.9 and flag_profile["strong_count"] == 0 and flag_profile["moderate_count"] >= 1:
            return "too_perfect_state"
        if (
            flag_profile["weak_count"] >= 3
            and flag_profile["strong_count"] == 0
            and final_score >= self.THRESHOLDS["delayed"]
            and final_score < self.THRESHOLDS["approved"]
            and automation_confidence < 0.7
        ):
            return "noise_overload"
        if (
            final_score >= self.THRESHOLDS["borderline_approved"]
            and signal_agreement_gap >= 0.28
            and event_confidence <= 0.55
        ):
            return "silent_conflict"
        return None

    def _uncertainty_profile(
        self,
        *,
        uncertainty_case: str | None,
        automation_confidence: float,
        final_score: float,
        payout_amount: float,
        flag_profile: Dict[str, Any],
    ) -> dict[str, Any]:
        if uncertainty_case is None:
            return {
                "case": None,
                "band": "stable" if automation_confidence >= self.MODERATE_CONFIDENCE_THRESHOLD else "guarded",
                "route": "standard",
                "explanation": "No contradiction or instability pattern dominated this decision.",
            }

        case_map = {
            "core_contradiction": {
                "band": "critical",
                "route": "review",
                "explanation": "Strong disruption signals conflict with trust/fraud posture, so review stays safer than automation.",
            },
            "too_perfect_state": {
                "band": "guarded",
                "route": "review",
                "explanation": "The profile looks unusually clean while moderate review flags are still present, so the system avoids blind approval.",
            },
            "noise_overload": {
                "band": "guarded",
                "route": "review",
                "explanation": "Multiple weak signals stacked without a strong blocker, so the system treats the pattern as noisy rather than clearly risky.",
            },
            "silent_conflict": {
                "band": "moderate",
                "route": "review",
                "explanation": "Borderline approval score is undermined by low agreement between disruption strength and event confidence.",
            },
        }
        profile = case_map[uncertainty_case]
        if payout_amount <= self.PAYOUT_CAPS["low_payout_confident"] and flag_profile["strong_count"] == 0:
            profile = {
                **profile,
                "band": "moderate" if profile["band"] == "guarded" else profile["band"],
            }
        return {"case": uncertainty_case, **profile}

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

    def _build_policy_context(
        self,
        *,
        final_score: float,
        disruption_score: float,
        event_confidence: float,
        adjusted_fraud: float,
        trust_score: float,
        payout_amount: float,
        automation_confidence: float,
        uncertainty_case: str | None,
        uncertainty_profile: dict[str, Any],
        pattern_taxonomy: dict[str, Any],
        flag_profile: Dict[str, Any],
        fraud_flags: list[str],
        auto_approve: bool,
        trusted_low_risk_approve: bool,
        auto_reject: bool,
        low_payout_confident_approve: bool,
        weak_signal_confident_approve: bool,
        false_review_safe_lane_approve: bool,
        device_micro_payout_approve: bool,
        cluster_micro_resolved_approve: bool,
        borderline_confident_approve: bool,
        threshold_score_approve: bool,
        cluster_context: dict[str, Any],
        gray_band_surface: str | None,
    ) -> dict[str, Any]:
        return {
            "final_score": final_score,
            "disruption_score": disruption_score,
            "event_confidence": event_confidence,
            "adjusted_fraud": adjusted_fraud,
            "trust_score": trust_score,
            "payout_amount": payout_amount,
            "automation_confidence": automation_confidence,
            "uncertainty_case": uncertainty_case,
            "uncertainty_profile": uncertainty_profile,
            "pattern_taxonomy": pattern_taxonomy,
            "flag_profile": flag_profile,
            "fraud_flags": fraud_flags,
            "auto_approve": auto_approve,
            "trusted_low_risk_approve": trusted_low_risk_approve,
            "auto_reject": auto_reject,
            "low_payout_confident_approve": low_payout_confident_approve,
            "weak_signal_confident_approve": weak_signal_confident_approve,
            "false_review_safe_lane_approve": false_review_safe_lane_approve,
            "device_micro_payout_approve": device_micro_payout_approve,
            "cluster_micro_resolved_approve": cluster_micro_resolved_approve,
            "borderline_confident_approve": borderline_confident_approve,
            "threshold_score_approve": threshold_score_approve,
            "cluster_context": cluster_context,
            "gray_band_surface": gray_band_surface,
            "in_gray_band": gray_band_surface is not None,
        }

    def _fraud_rules(self) -> tuple[PolicyRule, ...]:
        return (
            PolicyRule(
                "auto_reject_fraud_override",
                "fraud_layer",
                "rejected",
                "Claim rejected by high fraud pressure and low trust (score: {final_score}).",
                "Hard-stop severe fraud exposure.",
                "fraud_override",
                "minimize_fraud_leakage",
                lambda ctx: ctx["auto_reject"] or ctx["adjusted_fraud"] >= 0.70,
            ),
        )

    def _strong_approve_rules(self) -> tuple[PolicyRule, ...]:
        return (
            PolicyRule(
                "auto_approve_strong_signal_alignment",
                "strong_approve_layer",
                "approved",
                "Claim auto-approved by strong signal alignment (score: {final_score}).",
                "Approve clear high-signal claims.",
                "high_signal_alignment",
                "maximize_zero_touch",
                lambda ctx: ctx["auto_approve"],
            ),
            PolicyRule(
                "trusted_low_risk_approve",
                "strong_approve_layer",
                "approved",
                "Claim approved for trusted low-fraud profile despite mild review signals (score: {final_score}).",
                "Protect trusted workers with low fraud exposure.",
                "trust_relief",
                "maximize_zero_touch",
                lambda ctx: ctx["trusted_low_risk_approve"],
            ),
            PolicyRule(
                "threshold_score_approve",
                "strong_approve_layer",
                "approved",
                "Claim approved with sufficient confidence (score: {final_score}).",
                "Approve claims clearing the main confidence surface.",
                "threshold_surface",
                "balanced_automation",
                lambda ctx: ctx["threshold_score_approve"],
            ),
        )

    def _micro_lane_rules(self) -> tuple[PolicyRule, ...]:
        return (
            PolicyRule(
                "gray_band_low_payout_legit_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved in the low-payout gray-band lane because payout stayed small, trust held, and only weak legitimacy signals were present (score: {final_score}).",
                "Resolve low-payout legitimate claims inside the explicit gray band.",
                "low_payout_legit_surface",
                "reduce_false_reviews",
                lambda ctx: (
                    ctx["gray_band_surface"] == "low_payout_legit_surface"
                    and ctx["flag_profile"]["strong_count"] == 0
                    and ctx["uncertainty_case"] in {None, "noise_overload"}
                    and ctx["automation_confidence"] >= 0.52
                ),
            ),
            PolicyRule(
                "weak_signal_confident_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved because only weak review signals were present and confidence stayed stable (score: {final_score}).",
                "Approve weak-signal-only low-risk claims.",
                "weak_signal_surface",
                "reduce_false_reviews",
                lambda ctx: ctx["weak_signal_confident_approve"],
            ),
            PolicyRule(
                "low_payout_confident_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved because payout exposure stayed low and confidence remained stable (score: {final_score}).",
                "Approve low-exposure claims under stable confidence.",
                "low_payout_surface",
                "reduce_false_reviews",
                lambda ctx: ctx["low_payout_confident_approve"],
            ),
            PolicyRule(
                "false_review_safe_lane_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved in the calibrated weak-signal lane because stored review outcomes show this low-payout band is usually legitimate (score: {final_score}).",
                "Use stored outcomes to relieve known false-review pockets.",
                "calibrated_safe_lane",
                "reduce_false_reviews",
                lambda ctx: ctx["false_review_safe_lane_approve"],
            ),
            PolicyRule(
                "device_micro_payout_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved in the guarded device-only micro-payout lane because stored outcomes show isolated device risk is often noise at this exposure level (score: {final_score}).",
                "Guarded approval for isolated device-noise micro claims.",
                "device_micro_surface",
                "reduce_false_reviews",
                lambda ctx: ctx["device_micro_payout_approve"],
            ),
            PolicyRule(
                "cluster_micro_resolved_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved in the guarded cluster-device micro-payout lane because stored outcomes show this tiny high-confidence pocket is often legitimate (score: {final_score}).",
                "Guarded approval for classified coincidence-cluster micro claims.",
                "cluster_micro_surface",
                "reduce_false_reviews",
                lambda ctx: ctx["cluster_micro_resolved_approve"],
            ),
            PolicyRule(
                "borderline_confident_approve",
                "micro_payout_safe_lane",
                "approved",
                "Claim approved in the safe borderline band because trust, fraud, and confidence stayed stable (score: {final_score}).",
                "Approve stable borderline cases with low escalation pressure.",
                "borderline_surface",
                "balanced_automation",
                lambda ctx: ctx["borderline_confident_approve"],
            ),
        )

    def _uncertainty_rules(self) -> tuple[PolicyRule, ...]:
        return (
            PolicyRule(
                "uncertainty_core_contradiction_review",
                "ambiguity_resolver",
                "delayed",
                "Claim delayed for manual review because of core contradiction under borderline conditions (score: {final_score}).",
                "Escalate sharp contradiction between event strength and trust/fraud posture.",
                "uncertainty_contradiction",
                "protect_from_bad_automation",
                lambda ctx: ctx["uncertainty_case"] == "core_contradiction",
            ),
            PolicyRule(
                "uncertainty_too_perfect_state_review",
                "ambiguity_resolver",
                "delayed",
                "Claim delayed for manual review because of too perfect state under borderline conditions (score: {final_score}).",
                "Escalate profiles that look implausibly clean.",
                "uncertainty_implausible_cleanliness",
                "protect_from_bad_automation",
                lambda ctx: ctx["uncertainty_case"] == "too_perfect_state",
            ),
            PolicyRule(
                "uncertainty_silent_conflict_review",
                "ambiguity_resolver",
                "delayed",
                "Claim delayed for manual review because of silent conflict under borderline conditions (score: {final_score}).",
                "Escalate low-agreement borderline cases.",
                "uncertainty_silent_conflict",
                "protect_from_bad_automation",
                lambda ctx: ctx["uncertainty_case"] == "silent_conflict",
            ),
            PolicyRule(
                "uncertainty_noise_overload_micro_approve",
                "ambiguity_resolver",
                "approved",
                "Claim approved despite noisy weak-signal overlap because payout exposure stayed low and confidence remained within guarded bounds (score: {final_score}).",
                "Relieve noisy weak-signal micro claims with evidence-backed guardrails.",
                "uncertainty_noise_relief",
                "reduce_false_reviews",
                lambda ctx: (
                    ctx["uncertainty_case"] == "noise_overload"
                    and ctx["payout_amount"] <= self.GUARDRAILS["low_payout"]
                    and ctx["automation_confidence"] >= self.GUARDRAILS["low_confidence"]
                    and ctx["final_score"] >= self.FALSE_REVIEW_SCORE_FLOOR
                    and ctx["trust_score"] >= 0.45
                    and ctx["pattern_taxonomy"]["name"] == "weak_overlap_noise"
                    and ctx["flag_profile"]["strong_count"] == 0
                ),
            ),
            PolicyRule(
                "uncertainty_noise_overload_review",
                "ambiguity_resolver",
                "delayed",
                "Claim delayed for manual review because of noise overload under borderline conditions (score: {final_score}).",
                "Escalate noisy weak-signal claims that miss guarded relief conditions.",
                "uncertainty_noise_review",
                "protect_from_bad_automation",
                lambda ctx: ctx["uncertainty_case"] == "noise_overload",
            ),
        )

    def _fallback_rules(self) -> tuple[PolicyRule, ...]:
        return (
            PolicyRule(
                "gray_band_mid_trust_ambiguity_review",
                "review_fallback",
                "delayed",
                "Claim delayed because it sits in the gray band with mid-trust ambiguity that still needs human confirmation (score: {final_score}).",
                "Hold gray-band cases where trust is not low enough to reject and not strong enough to auto-approve.",
                "mid_trust_ambiguity_surface",
                "bounded_risk_control",
                lambda ctx: ctx["gray_band_surface"] == "mid_trust_ambiguity_surface",
            ),
            PolicyRule(
                "gray_band_early_fraud_signal_review",
                "review_fallback",
                "delayed",
                "Claim delayed because early fraud pressure is present inside the gray band (score: {final_score}).",
                "Protect the system from early fraud signals that are not yet strong enough for rejection.",
                "early_fraud_signal_surface",
                "protect_from_bad_automation",
                lambda ctx: ctx["gray_band_surface"] == "early_fraud_signal_surface",
            ),
            PolicyRule(
                "gray_band_cluster_sensitive_review",
                "review_fallback",
                "delayed",
                "Claim delayed because cluster-sensitive behavior is present inside the gray band (score: {final_score}).",
                "Route cluster-sensitive gray-band claims through review until cluster handling is fully hardened.",
                "cluster_sensitive_surface",
                "protect_from_bad_automation",
                lambda ctx: ctx["gray_band_surface"] == "cluster_sensitive_surface",
            ),
            PolicyRule(
                "below_delayed_threshold_reject",
                "review_fallback",
                "rejected",
                "Claim rejected (score: {final_score}).",
                "Reject claims below the minimum viability surface.",
                "fallback_reject",
                "bounded_risk_control",
                lambda ctx: ctx["final_score"] < self.THRESHOLDS["delayed"],
            ),
            PolicyRule(
                "standard_review_fallback",
                "review_fallback",
                "delayed",
                "Claim delayed for manual review (score: {final_score}).",
                "Default safe review route when no prior layer claims the case.",
                "fallback_review",
                "bounded_risk_control",
                lambda ctx: True,
            ),
        )

    def _policy_registry(self) -> dict[str, tuple[PolicyRule, ...]]:
        return {
            "fraud_layer": self._fraud_rules(),
            "strong_approve_layer": self._strong_approve_rules(),
            "micro_payout_safe_lane": self._micro_lane_rules(),
            "ambiguity_resolver": self._uncertainty_rules(),
            "review_fallback": self._fallback_rules(),
        }

    def _matching_rules(self, rules: tuple[PolicyRule, ...], context: dict[str, Any]) -> list[PolicyRule]:
        return [rule for rule in rules if rule.matcher(context)]

    def _resolve_policy(self, context: dict[str, Any]) -> tuple[str, dict[str, str], str]:
        registry = self._policy_registry()
        for layer in self.POLICY_LAYERS:
            matches = self._matching_rules(registry[layer], context)
            if layer == "ambiguity_resolver" and context["uncertainty_case"] is not None and len(matches) != 1:
                raise RuntimeError(
                    f"Expected exactly one uncertainty rule for case {context['uncertainty_case']}, got {len(matches)}."
                )
            if matches:
                rule = matches[0]
                return rule.decision, self._policy_resolution(rule.layer, rule.rule_id), rule.explanation_template
        raise RuntimeError("No policy rule matched; review fallback registry is incomplete.")

    def _policy_resolution(self, layer: str, rule_id: str) -> dict[str, str]:
        return {
            "policy_layer": layer,
            "rule_id": rule_id,
            "decision_policy_version": self.POLICY_VERSION,
        }

    def _rule_metadata(self, layer: str, rule_id: str) -> dict[str, str]:
        registry = self._policy_registry()
        for rule in registry[layer]:
            if rule.rule_id == rule_id:
                return {
                    "purpose": rule.purpose,
                    "surface": rule.surface,
                    "risk_expectation": rule.risk_expectation,
                }
        return {
            "purpose": "unknown",
            "surface": "unknown",
            "risk_expectation": "unknown",
        }

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
        movement_signal = self._flag_signal_value(fraud_result, "movement")
        gps_spoof_detected = movement_signal >= 0.8
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

        automation_confidence = self._automation_confidence(
            disruption_score=disruption_score,
            event_confidence=event_confidence,
            fraud_result=fraud_result,
            trust_score=trust_score,
            feedback_result=feedback_result,
            flag_profile=flag_profile,
        )
        uncertainty_case = self._uncertainty_case(
            final_score=final_score,
            disruption_score=disruption_score,
            event_confidence=event_confidence,
            adjusted_fraud=adjusted_fraud,
            trust_score=trust_score,
            flag_profile=flag_profile,
            automation_confidence=automation_confidence,
        )
        uncertainty_profile = self._uncertainty_profile(
            uncertainty_case=uncertainty_case,
            automation_confidence=automation_confidence,
            final_score=final_score,
            payout_amount=payout_amount,
            flag_profile=flag_profile,
        )
        pattern_taxonomy = self._pattern_taxonomy(
            fraud_flags=fraud_flags,
            flag_profile=flag_profile,
            payout_amount=payout_amount,
            adjusted_fraud=adjusted_fraud,
            trust_score=trust_score,
            event_confidence=event_confidence,
            automation_confidence=automation_confidence,
            final_score=final_score,
        )
        cluster_context = self._classify_cluster_context(
            fraud_flags=fraud_flags,
            payout_amount=payout_amount,
            adjusted_fraud=adjusted_fraud,
            trust_score=trust_score,
            event_confidence=event_confidence,
            automation_confidence=automation_confidence,
            final_score=final_score,
            flag_profile=flag_profile,
        )
        gray_band_surface = self._gray_band_surface(
            final_score=final_score,
            payout_amount=payout_amount,
            trust_score=trust_score,
            adjusted_fraud=adjusted_fraud,
            fraud_flags=fraud_flags,
            flag_profile=flag_profile,
            uncertainty_case=uncertainty_case,
            cluster_context=cluster_context,
        )
        auto_approve = (
            adjusted_fraud <= 0.18
            and trust_score >= 0.09
            and event_confidence >= 0.75
            and disruption_score >= 0.65
            and cluster_context["routing"] != "strong_review"
            and uncertainty_case != "too_perfect_state"
        )
        trusted_low_risk_approve = (
            adjusted_fraud <= 0.18
            and trust_score >= 0.20
            and event_confidence >= 0.70
            and final_score >= 0.55
            and set(fraud_flags).issubset(self.LOW_RISK_REVIEW_FLAGS)
            and uncertainty_case != "core_contradiction"
        )
        auto_reject = (
            adjusted_fraud >= 0.55
            and len(fraud_flags) >= 3
            and trust_score <= 0.35
        )
        low_payout_confident_approve = (
            payout_amount <= self.PAYOUT_CAPS["low_payout_confident"]
            and adjusted_fraud <= 0.30
            and trust_score >= 0.25
            and event_confidence >= 0.65
            and final_score >= 0.55
            and automation_confidence >= 0.60
            and flag_profile["strong_count"] == 0
            and cluster_context["routing"] != "strong_review"
            and uncertainty_case not in {"core_contradiction", "too_perfect_state"}
        )
        weak_signal_confident_approve = (
            flag_profile["noise_only"]
            and adjusted_fraud <= 0.24
            and trust_score >= 0.25
            and event_confidence >= 0.65
            and final_score >= 0.55
            and automation_confidence >= 0.55
            and payout_amount <= self.PAYOUT_CAPS["weak_signal_confident"]
            and cluster_context["routing"] != "strong_review"
            and uncertainty_case not in {"core_contradiction", "too_perfect_state"}
        )
        false_review_safe_lane_approve = (
            pattern_taxonomy["name"] == "weak_overlap_noise"
            and self.FALSE_REVIEW_SCORE_FLOOR <= final_score < self.THRESHOLDS["approved"]
            and payout_amount <= self.PAYOUT_CAPS["false_review_safe_lane"]
            and adjusted_fraud <= 0.30
            and trust_score >= 0.30
            and event_confidence >= 0.62
            and automation_confidence >= 0.57
            and cluster_context["routing"] != "strong_review"
            and uncertainty_case not in {"core_contradiction", "too_perfect_state", "silent_conflict"}
        )
        device_micro_payout_approve = (
            pattern_taxonomy["name"] == "device_micro_noise"
            and adjusted_fraud <= 0.12
            and payout_amount <= self.PAYOUT_CAPS["device_micro_payout"]
            and trust_score >= 0.60
            and automation_confidence >= 0.45
            and uncertainty_case not in {"core_contradiction", "too_perfect_state", "silent_conflict"}
        )
        cluster_micro_resolved_approve = (
            pattern_taxonomy["name"] == "cluster_micro_resolved"
            and payout_amount <= self.PAYOUT_CAPS["cluster_micro_payout"]
            and adjusted_fraud <= 0.16
            and trust_score >= 0.28
            and event_confidence >= 0.90
            and automation_confidence >= 0.52
            and uncertainty_case not in {"core_contradiction", "too_perfect_state", "silent_conflict"}
        )
        borderline_confident_approve = (
            final_score >= self.THRESHOLDS["borderline_approved"]
            and adjusted_fraud <= 0.30
            and trust_score >= 0.30
            and event_confidence >= 0.65
            and automation_confidence >= 0.60
            and flag_profile["strong_count"] == 0
            and flag_profile["moderate_count"] == 0
            and payout_amount <= self.PAYOUT_CAPS["borderline_confident"]
            and cluster_context["routing"] != "strong_review"
            and uncertainty_case not in {"core_contradiction", "silent_conflict"}
        )
        threshold_score_approve = final_score >= self.THRESHOLDS["approved"] and (
            final_score >= 0.78 or automation_confidence >= 0.56
        ) and uncertainty_case not in {"core_contradiction", "too_perfect_state", "silent_conflict"} and cluster_context["routing"] != "strong_review"

        policy_context = self._build_policy_context(
            final_score=final_score,
            disruption_score=disruption_score,
            event_confidence=event_confidence,
            adjusted_fraud=adjusted_fraud,
            trust_score=trust_score,
            payout_amount=payout_amount,
            automation_confidence=automation_confidence,
            uncertainty_case=uncertainty_case,
            uncertainty_profile=uncertainty_profile,
            pattern_taxonomy=pattern_taxonomy,
            flag_profile=flag_profile,
            fraud_flags=fraud_flags,
            auto_approve=auto_approve,
            trusted_low_risk_approve=trusted_low_risk_approve,
            auto_reject=auto_reject,
            low_payout_confident_approve=low_payout_confident_approve,
            weak_signal_confident_approve=weak_signal_confident_approve,
            false_review_safe_lane_approve=false_review_safe_lane_approve,
            device_micro_payout_approve=device_micro_payout_approve,
            cluster_micro_resolved_approve=cluster_micro_resolved_approve,
            borderline_confident_approve=borderline_confident_approve,
            threshold_score_approve=threshold_score_approve,
            cluster_context=cluster_context,
            gray_band_surface=gray_band_surface,
        )
        decision, policy, explanation_template = self._resolve_policy(policy_context)
        if gps_spoof_detected:
            strong_review_flags = {"duplicate", "timing", "income_inflation", "cluster"}
            if adjusted_fraud >= 0.35 or trust_score <= 0.35 or strong_review_flags.intersection(fraud_flags):
                decision = "rejected"
                policy = self._policy_resolution("fraud_layer", "gps_spoof_reject_override")
                explanation_template = "Claim rejected because RideShield detected GPS spoofing-class movement patterns."
            else:
                decision = "delayed"
                policy = self._policy_resolution("review_fallback", "gps_spoof_review_override")
                explanation_template = "Claim delayed because RideShield detected GPS spoofing-class movement patterns."
        explanation = explanation_template.format(final_score=final_score)
        rule_metadata = self._rule_metadata(policy["policy_layer"], policy["rule_id"])

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
                or false_review_safe_lane_approve
                or device_micro_payout_approve
                or cluster_micro_resolved_approve
                or borderline_confident_approve
            ),
            auto_reject=auto_reject,
            feedback_result=feedback_result,
        )
        reason_labels = self._reason_labels(
            fraud_flags=fraud_flags,
            trust_score=trust_score,
            event_confidence=event_confidence,
            adjusted_fraud=adjusted_fraud,
        )
        primary_reason = reason_labels[0]

        logger.info({
            "decision": decision,
            "fraud_score": adjusted_fraud,
            "trust_score": trust_score,
            "final_score": final_score,
            "confidence": decision_confidence,
            "reason": primary_reason
        })

        return {
            "final_score": final_score,
            "decision": decision,
            "explanation": explanation,
            "decision_policy_version": self.POLICY_VERSION,
            "policy_layer": policy["policy_layer"],
            "rule_id": policy["rule_id"],
            "decision_confidence": decision_confidence,
            "decision_confidence_band": self._confidence_band(decision_confidence),
            "primary_reason": primary_reason,
            "reason_labels": reason_labels,
            "uncertainty": uncertainty_profile,
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
                "policy_layers": self.POLICY_LAYERS,
                "policy_layer": policy["policy_layer"],
                "rule_id": policy["rule_id"],
                "rule_metadata": rule_metadata,
                "guardrails": self.GUARDRAILS,
                "uncertainty_case": uncertainty_profile["case"],
                "pattern_taxonomy": pattern_taxonomy["name"],
                "pattern_manual_bias": pattern_taxonomy["manual_bias"],
                "gray_band_surface": gray_band_surface,
                "cluster_type": cluster_context["type"],
                "cluster_routing": cluster_context["routing"],
                "cluster_raw_penalty_active": cluster_context["raw_penalty_active"],
                "gps_spoof_detected": gps_spoof_detected,
            },
            "inputs": {
                "disruption_score": disruption_score,
                "event_confidence": event_confidence,
                "adjusted_fraud_score": adjusted_fraud,
                "raw_fraud_score": fraud_result["raw_fraud_score"],
                "trust_score": trust_score,
                "fraud_flags": fraud_flags,
                "payout_amount": payout_amount,
                "low_payout_threshold": self.GUARDRAILS["low_payout"],
                "high_payout_threshold": self.GUARDRAILS["high_payout"],
                "high_trust_threshold": self.GUARDRAILS["high_trust"],
                "low_confidence_threshold": self.GUARDRAILS["low_confidence"],
                "gray_band_low": self.GUARDRAILS["gray_band_low"],
                "gray_band_high": self.GUARDRAILS["gray_band_high"],
                "gray_band_surface": gray_band_surface,
                "weak_signal_confident_approve": weak_signal_confident_approve,
                "low_payout_confident_approve": low_payout_confident_approve,
                "false_review_safe_lane_approve": false_review_safe_lane_approve,
                "device_micro_payout_approve": device_micro_payout_approve,
                "cluster_micro_resolved_approve": cluster_micro_resolved_approve,
                "borderline_confident_approve": borderline_confident_approve,
                "auto_approve": auto_approve,
                "trusted_low_risk_approve": trusted_low_risk_approve,
                "auto_reject": auto_reject,
                "gps_spoof_detected": gps_spoof_detected,
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
