"""Analytics API for admin dashboard metrics and operational summaries."""

import asyncio
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.core.decision_memory import replay_decision_log
from backend.core.forecast_engine import forecast_engine
from backend.core.fraud_model_service import fraud_model_service
from backend.core.risk_model_service import risk_model_service
from backend.core.session_auth import require_admin_session
from backend.core.trigger_scheduler import trigger_scheduler
from backend.database import async_session_factory, get_db
from backend.db.models import AuditLog, Claim, DecisionLog, Event, Payout, Policy, Worker, WorkerActivity
from backend.utils.time import utc_now_naive

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


async def _forecast_city_snapshot(city: str, horizon_hours: int) -> dict:
    async with async_session_factory() as forecast_db:
        return await forecast_engine.forecast_city(forecast_db, city, horizon_hours=horizon_hours)


def forecast_band(score: float) -> str:
    if score < 0.3:
        return "low"
    if score < 0.55:
        return "guarded"
    if score < 0.75:
        return "elevated"
    return "critical"


def _humanize_label(value: str | None) -> str:
    if not value:
        return "signal alignment"
    return " ".join(part.capitalize() for part in str(value).split("_") if part)


def _review_flag_label(value: str | None) -> str:
    mapping = {
        "movement": "movement anomaly",
        "pre_activity": "weak pre-event activity",
        "timing": "policy timing risk",
        "duplicate": "duplicate claim pressure",
        "cluster": "cluster fraud pressure",
        "income_inflation": "income inflation pressure",
        "device": "device risk",
    }
    if value in mapping:
        return mapping[value]
    return _humanize_label(value).lower()


def _is_zero_touch_approved(claim: Claim) -> bool:
    return claim.status == "approved" and not claim.reviewed_by


def _review_driver_labels(claim: Claim) -> list[str]:
    breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    labels: list[str] = []
    seen: set[str] = set()

    def add_label(value: str | None) -> None:
        if not value:
            return
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        labels.append(normalized)

    add_label(breakdown.get("primary_reason"))
    fraud_model = breakdown.get("fraud_model") if isinstance(breakdown.get("fraud_model"), dict) else {}
    top_factors = fraud_model.get("top_factors") if isinstance(fraud_model.get("top_factors"), list) else []
    for factor in top_factors[:3]:
        add_label(factor.get("label"))
    inputs = breakdown.get("inputs") if isinstance(breakdown.get("inputs"), dict) else {}
    flags = inputs.get("fraud_flags") if isinstance(inputs.get("fraud_flags"), list) else []
    for flag in flags[:3]:
        add_label(_review_flag_label(flag))
    event_confidence = inputs.get("event_confidence")
    try:
        if event_confidence is not None and float(event_confidence) <= 0.75:
            add_label("event confidence")
    except (TypeError, ValueError):
        pass
    if not labels:
        add_label("signal alignment")
    return labels


def _incident_key(claim: Claim) -> str:
    zone = claim.event.zone if claim.event else "zone"
    created_at = claim.created_at.isoformat() if claim.created_at else "unknown"
    bucket = created_at[:13]
    return f"{claim.worker_id}|{zone}|{bucket}"


def _review_insights(driver_counts: dict[str, int], incident_labels: list[set[str]], total_incidents: int) -> dict:
    weak_signal_labels = {
        "movement anomaly",
        "weak pre-event activity",
        "event confidence",
        "signal alignment requires review",
    }
    low_trust_count = sum(1 for labels in incident_labels if "worker trust score" in labels)
    weak_signal_count = sum(1 for labels in incident_labels if labels & weak_signal_labels)
    return {
        "weak_signal_overlap_share": round((weak_signal_count / max(1, total_incidents)) * 100),
        "low_trust_share": round((low_trust_count / max(1, total_incidents)) * 100),
    }


def _decision_log_reason_labels(entry: DecisionLog) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()

    def add_label(value: str | None) -> None:
        if not value:
            return
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        labels.append(normalized)

    output_snapshot = entry.output_snapshot if isinstance(entry.output_snapshot, dict) else {}
    decision_payload = output_snapshot.get("decision") if isinstance(output_snapshot.get("decision"), dict) else {}
    add_label(decision_payload.get("primary_reason"))

    feature_snapshot = entry.feature_snapshot if isinstance(entry.feature_snapshot, dict) else {}
    decision_inputs = feature_snapshot.get("decision_inputs") if isinstance(feature_snapshot.get("decision_inputs"), dict) else {}
    fraud_result = decision_inputs.get("fraud_result") if isinstance(decision_inputs.get("fraud_result"), dict) else {}
    for factor in fraud_result.get("top_factors") or []:
        if isinstance(factor, dict):
            add_label(factor.get("label"))
    for flag in fraud_result.get("flags") or []:
        add_label(_review_flag_label(flag))
    if not labels:
        add_label("signal alignment")
    return labels


def _decision_log_policy_metadata(entry: DecisionLog) -> dict[str, str]:
    output_snapshot = entry.output_snapshot if isinstance(entry.output_snapshot, dict) else {}
    decision_payload = output_snapshot.get("decision") if isinstance(output_snapshot.get("decision"), dict) else {}
    feature_snapshot = entry.feature_snapshot if isinstance(entry.feature_snapshot, dict) else {}
    claim_features = feature_snapshot.get("claim_features") if isinstance(feature_snapshot.get("claim_features"), dict) else {}
    return {
        "policy_layer": str(decision_payload.get("policy_layer") or "unknown"),
        "rule_id": str(decision_payload.get("rule_id") or "unknown"),
        "surface": str(claim_features.get("surface") or decision_payload.get("surface") or "unknown"),
        "risk_expectation": str(
            claim_features.get("risk_expectation") or decision_payload.get("risk_expectation") or "unknown"
        ),
    }


def _decision_log_traffic_source(entry: DecisionLog) -> str:
    context_snapshot = entry.context_snapshot if isinstance(entry.context_snapshot, dict) else {}
    return str(context_snapshot.get("traffic_source") or "baseline")


def _score_band(final_score: float) -> str:
    if final_score < 0.45:
        return "reject_band"
    if final_score < 0.60:
        return "review_band_low"
    if final_score < 0.65:
        return "review_band_high"
    return "approve_band"


def _false_review_score_band(final_score: float) -> str:
    if final_score < 0.45:
        return "lt_0.45"
    if final_score < 0.55:
        return "0.45_0.55"
    if final_score < 0.60:
        return "0.55_0.60"
    if final_score < 0.65:
        return "0.60_0.65"
    return "ge_0.65"


def _false_review_payout_band(payout_amount: float) -> str:
    if payout_amount < 75:
        return "lt_75"
    if payout_amount < 125:
        return "75_125"
    if payout_amount < 200:
        return "125_200"
    return "ge_200"


def _build_decision_memory_summary(decision_logs: list[DecisionLog]) -> dict:
    claim_created_logs = [log for log in decision_logs if log.lifecycle_stage == "claim_created"]
    resolved_logs = [log for log in decision_logs if log.final_label]
    delayed_system_logs = [log for log in resolved_logs if log.system_decision == "delayed"]
    false_review_logs = [log for log in delayed_system_logs if log.final_label == "legit"]
    false_reject_logs = [log for log in resolved_logs if log.system_decision == "rejected" and log.final_label == "legit"]
    manual_override_logs = [log for log in decision_logs if log.lifecycle_stage in {"manual_resolution", "backfill_resolution"}]

    route_counts = {"approved": 0, "delayed": 0, "rejected": 0}
    score_bands = {"reject_band": 0, "review_band_low": 0, "review_band_high": 0, "approve_band": 0}
    policy_versions: dict[str, int] = {}
    fraud_model_versions: dict[str, int] = {}
    false_review_driver_counts: dict[str, int] = {}
    rule_counts: dict[str, int] = {}
    layer_counts: dict[str, int] = {}
    traffic_source_counts: dict[str, int] = {}

    for log in claim_created_logs:
        if log.system_decision in route_counts:
            route_counts[log.system_decision] += 1
        score_bands[_score_band(float(log.final_score or 0))] += 1
        policy_versions[log.decision_policy_version] = policy_versions.get(log.decision_policy_version, 0) + 1
        model_versions = log.model_versions if isinstance(log.model_versions, dict) else {}
        fraud_model = str(model_versions.get("fraud_model", "unknown"))
        fraud_model_versions[fraud_model] = fraud_model_versions.get(fraud_model, 0) + 1
        policy_metadata = _decision_log_policy_metadata(log)
        layer = policy_metadata["policy_layer"]
        rule_id = policy_metadata["rule_id"]
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
        rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
        traffic_source = _decision_log_traffic_source(log)
        traffic_source_counts[traffic_source] = traffic_source_counts.get(traffic_source, 0) + 1

    for log in false_review_logs:
        for label in _decision_log_reason_labels(log):
            false_review_driver_counts[label] = false_review_driver_counts.get(label, 0) + 1

    top_false_review_drivers = [
        {
            "label": label,
            "count": count,
            "share": round((count / max(1, len(false_review_logs))) * 100),
        }
        for label, count in sorted(false_review_driver_counts.items(), key=lambda item: (-item[1], item[0]))
    ][:3]
    top_policy_rules = [
        {
            "rule_id": rule_id,
            "count": count,
            "share": round((count / max(1, len(claim_created_logs))) * 100, 1),
        }
        for rule_id, count in sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))
    ][:5]

    return {
        "window_logged_decisions": len(decision_logs),
        "claim_created_rows": len(claim_created_logs),
        "resolved_labels": len(resolved_logs),
        "route_counts": route_counts,
        "score_band_distribution": score_bands,
        "manual_override_rate": round((len(manual_override_logs) / max(1, len(claim_created_logs))) * 100, 1),
        "false_review_count": len(false_review_logs),
        "false_review_rate": round((len(false_review_logs) / max(1, len(delayed_system_logs))) * 100, 1),
        "false_reject_count": len(false_reject_logs),
        "false_reject_rate": round((len(false_reject_logs) / max(1, len([log for log in resolved_logs if log.system_decision == 'rejected']))) * 100, 1),
        "policy_versions": policy_versions,
        "fraud_model_versions": fraud_model_versions,
        "top_false_review_drivers": top_false_review_drivers,
        "policy_layer_counts": layer_counts,
        "top_policy_rules": top_policy_rules,
        "traffic_source_counts": traffic_source_counts,
    }


def _build_false_review_pattern_summary(decision_logs: list[DecisionLog]) -> dict:
    claim_created_logs = {
        str(log.claim_id): log
        for log in decision_logs
        if log.lifecycle_stage == "claim_created"
    }
    resolved_logs = [
        log
        for log in decision_logs
        if log.final_label and str(log.claim_id) in claim_created_logs
    ]
    false_reviews = [
        (claim_created_logs[str(log.claim_id)], log)
        for log in resolved_logs
        if claim_created_logs[str(log.claim_id)].system_decision == "delayed" and log.final_label == "legit"
    ]

    by_score_band: dict[str, int] = {}
    by_payout_band: dict[str, int] = {}
    by_flag_combo: dict[str, int] = {}
    by_surface: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    by_traffic_source: dict[str, int] = {}
    pattern_examples: dict[str, list[dict]] = {}

    for created_log, _ in false_reviews:
        score = float(created_log.final_score or 0)
        payout = float(created_log.payout_amount or 0)
        score_band = _false_review_score_band(score)
        payout_band = _false_review_payout_band(payout)
        by_score_band[score_band] = by_score_band.get(score_band, 0) + 1
        by_payout_band[payout_band] = by_payout_band.get(payout_band, 0) + 1

        feature_snapshot = created_log.feature_snapshot if isinstance(created_log.feature_snapshot, dict) else {}
        decision_inputs = feature_snapshot.get("decision_inputs") if isinstance(feature_snapshot.get("decision_inputs"), dict) else {}
        fraud_result = decision_inputs.get("fraud_result") if isinstance(decision_inputs.get("fraud_result"), dict) else {}
        flags = sorted(str(flag) for flag in (fraud_result.get("flags") or []))
        combo_key = "+".join(flags) if flags else "no_flags"
        by_flag_combo[combo_key] = by_flag_combo.get(combo_key, 0) + 1
        policy_metadata = _decision_log_policy_metadata(created_log)
        by_surface[policy_metadata["surface"]] = by_surface.get(policy_metadata["surface"], 0) + 1
        by_rule[policy_metadata["rule_id"]] = by_rule.get(policy_metadata["rule_id"], 0) + 1
        traffic_source = _decision_log_traffic_source(created_log)
        by_traffic_source[traffic_source] = by_traffic_source.get(traffic_source, 0) + 1

        examples = pattern_examples.setdefault(combo_key, [])
        if len(examples) < 3:
            examples.append(
                {
                    "claim_id": str(created_log.claim_id),
                    "score": round(score, 3),
                    "payout": round(payout, 2),
                    "fraud_score": round(float(created_log.fraud_score or 0), 3),
                    "trust_score": round(float(created_log.trust_score or 0), 3),
                }
            )

    dominant_patterns = [
        {
            "flags": combo_key.split("+") if combo_key != "no_flags" else [],
            "count": count,
            "share": round((count / max(1, len(false_reviews))) * 100, 1),
            "examples": pattern_examples.get(combo_key, []),
        }
        for combo_key, count in sorted(by_flag_combo.items(), key=lambda item: (-item[1], item[0]))
    ][:5]
    top_surfaces = [
        {
            "surface": surface,
            "count": count,
            "share": round((count / max(1, len(false_reviews))) * 100, 1),
        }
        for surface, count in sorted(by_surface.items(), key=lambda item: (-item[1], item[0]))
    ][:5]
    top_rules = [
        {
            "rule_id": rule_id,
            "count": count,
            "share": round((count / max(1, len(false_reviews))) * 100, 1),
        }
        for rule_id, count in sorted(by_rule.items(), key=lambda item: (-item[1], item[0]))
    ][:5]

    return {
        "false_review_count": len(false_reviews),
        "score_band_distribution": by_score_band,
        "payout_band_distribution": by_payout_band,
        "dominant_patterns": dominant_patterns,
        "surface_distribution": by_surface,
        "top_surfaces": top_surfaces,
        "top_rules": top_rules,
        "traffic_source_distribution": by_traffic_source,
    }


def _build_policy_replay_summary(decision_logs: list[DecisionLog]) -> dict:
    claim_created_logs = [
        log for log in decision_logs if log.lifecycle_stage == "claim_created"
    ]
    stored_route_counts: dict[str, int] = {}
    replay_route_counts: dict[str, int] = {}
    transitions: dict[str, int] = {}
    delayed_to_approved_examples: list[dict] = []
    approved_to_delayed_examples: list[dict] = []
    by_surface_transitions: dict[str, dict[str, int]] = {}
    by_source_transitions: dict[str, dict[str, int]] = {}
    matches = 0

    for log in claim_created_logs:
        stored = log.system_decision or log.resulting_status
        replayed = replay_decision_log(log)
        replay_decision = replayed["decision"]
        stored_route_counts[stored] = stored_route_counts.get(stored, 0) + 1
        replay_route_counts[replay_decision] = replay_route_counts.get(replay_decision, 0) + 1
        transition_key = f"{stored}->{replay_decision}"
        transitions[transition_key] = transitions.get(transition_key, 0) + 1
        if stored == replay_decision:
            matches += 1

        feature_snapshot = log.feature_snapshot if isinstance(log.feature_snapshot, dict) else {}
        decision_inputs = feature_snapshot.get("decision_inputs") if isinstance(feature_snapshot.get("decision_inputs"), dict) else {}
        fraud_result = decision_inputs.get("fraud_result") if isinstance(decision_inputs.get("fraud_result"), dict) else {}
        flags = list(fraud_result.get("flags") or [])
        example_payload = {
            "claim_id": str(log.claim_id),
            "stored": stored,
            "replayed": replay_decision,
            "score": round(float(log.final_score or 0), 3),
            "payout": round(float(log.payout_amount or 0), 2),
            "flags": flags,
        }
        policy_metadata = _decision_log_policy_metadata(log)
        surface = policy_metadata["surface"]
        surface_entry = by_surface_transitions.setdefault(surface, {})
        surface_entry[transition_key] = surface_entry.get(transition_key, 0) + 1
        traffic_source = _decision_log_traffic_source(log)
        source_entry = by_source_transitions.setdefault(traffic_source, {})
        source_entry[transition_key] = source_entry.get(transition_key, 0) + 1
        if stored == "delayed" and replay_decision == "approved" and len(delayed_to_approved_examples) < 5:
            delayed_to_approved_examples.append(example_payload)
        if stored == "approved" and replay_decision == "delayed" and len(approved_to_delayed_examples) < 5:
            approved_to_delayed_examples.append(example_payload)

    return {
        "rows_replayed": len(claim_created_logs),
        "match_rate": round((matches / max(1, len(claim_created_logs))) * 100, 1),
        "stored_route_counts": stored_route_counts,
        "replay_route_counts": replay_route_counts,
        "transitions": transitions,
        "delayed_to_approved_count": transitions.get("delayed->approved", 0),
        "approved_to_delayed_count": transitions.get("approved->delayed", 0),
        "rejected_to_approved_count": transitions.get("rejected->approved", 0),
        "delayed_to_approved_examples": delayed_to_approved_examples,
        "approved_to_delayed_examples": approved_to_delayed_examples,
        "surface_transitions": by_surface_transitions,
        "source_transitions": by_source_transitions,
    }


def _build_policy_health_summary(decision_logs: list[DecisionLog]) -> dict:
    claim_created_logs = [log for log in decision_logs if log.lifecycle_stage == "claim_created"]
    resolved_by_claim = {
        str(log.claim_id): log
        for log in decision_logs
        if log.final_label and str(log.claim_id)
    }

    rule_totals: dict[str, int] = {}
    surface_totals: dict[str, int] = {}
    rule_false_reviews: dict[str, int] = {}
    surface_false_reviews: dict[str, int] = {}

    auto_approved = 0
    delayed = 0

    for log in claim_created_logs:
        metadata = _decision_log_policy_metadata(log)
        rule_id = metadata["rule_id"]
        surface = metadata["surface"]
        rule_totals[rule_id] = rule_totals.get(rule_id, 0) + 1
        surface_totals[surface] = surface_totals.get(surface, 0) + 1
        if log.system_decision == "approved":
            auto_approved += 1
        if log.system_decision == "delayed":
            delayed += 1

        resolved = resolved_by_claim.get(str(log.claim_id))
        if resolved and log.system_decision == "delayed" and resolved.final_label == "legit":
            rule_false_reviews[rule_id] = rule_false_reviews.get(rule_id, 0) + 1
            surface_false_reviews[surface] = surface_false_reviews.get(surface, 0) + 1

    def build_rankings(totals: dict[str, int], false_reviews: dict[str, int], key_name: str) -> list[dict]:
        rows = []
        for key, total in totals.items():
            friction = false_reviews.get(key, 0)
            friction_rate = round((friction / max(1, total)) * 100, 1)
            rows.append(
                {
                    key_name: key,
                    "count": total,
                    "false_review_count": friction,
                    "friction_rate": friction_rate,
                    "impact_score": round(total * (friction_rate / 100), 2),
                }
            )
        return sorted(rows, key=lambda item: (-item["false_review_count"], -item["friction_rate"], -item["count"], item[key_name]))

    top_friction_rules = build_rankings(rule_totals, rule_false_reviews, "rule_id")[:5]
    top_friction_surfaces = build_rankings(surface_totals, surface_false_reviews, "surface")[:5]

    top_rule_count = max(rule_totals.values(), default=0)
    top_surface_count = max(surface_totals.values(), default=0)
    false_review_total = sum(rule_false_reviews.values())

    return {
        "friction_score": round((false_review_total / max(1, len(claim_created_logs))) * 100, 1),
        "automation_efficiency": round((auto_approved / max(1, len(claim_created_logs))) * 100, 1),
        "review_load": round((delayed / max(1, len(claim_created_logs))) * 100, 1),
        "rule_concentration": round((top_rule_count / max(1, len(claim_created_logs))) * 100, 1),
        "surface_imbalance": round((top_surface_count / max(1, len(claim_created_logs))) * 100, 1),
        "top_friction_rules": top_friction_rules,
        "top_friction_surfaces": top_friction_surfaces,
    }


def _build_source_comparison_summary(decision_logs: list[DecisionLog]) -> dict:
    claim_created_logs = [log for log in decision_logs if log.lifecycle_stage == "claim_created"]
    resolved_by_claim = {
        str(log.claim_id): log
        for log in decision_logs
        if log.final_label and str(log.claim_id)
    }

    source_rows: dict[str, dict] = {}
    for log in claim_created_logs:
        source = _decision_log_traffic_source(log)
        row = source_rows.setdefault(
            source,
            {
                "claim_created_rows": 0,
                "auto_approved": 0,
                "delayed": 0,
                "false_reviews": 0,
                "rule_counts": {},
                "surface_counts": {},
            },
        )
        row["claim_created_rows"] += 1
        if log.system_decision == "approved":
            row["auto_approved"] += 1
        if log.system_decision == "delayed":
            row["delayed"] += 1
        metadata = _decision_log_policy_metadata(log)
        rule_id = metadata["rule_id"]
        surface = metadata["surface"]
        row["rule_counts"][rule_id] = row["rule_counts"].get(rule_id, 0) + 1
        row["surface_counts"][surface] = row["surface_counts"].get(surface, 0) + 1

        resolved = resolved_by_claim.get(str(log.claim_id))
        if resolved and log.system_decision == "delayed" and resolved.final_label == "legit":
            row["false_reviews"] += 1

    comparisons = {}
    total_rows = len(claim_created_logs)
    for source, row in source_rows.items():
        top_rule = sorted(row["rule_counts"].items(), key=lambda item: (-item[1], item[0]))[:1]
        top_surface = sorted(row["surface_counts"].items(), key=lambda item: (-item[1], item[0]))[:1]
        comparisons[source] = {
            "claim_created_rows": row["claim_created_rows"],
            "share_of_window": round((row["claim_created_rows"] / max(1, total_rows)) * 100, 1),
            "automation_efficiency": round((row["auto_approved"] / max(1, row["claim_created_rows"])) * 100, 1),
            "review_load": round((row["delayed"] / max(1, row["claim_created_rows"])) * 100, 1),
            "false_review_rate": round((row["false_reviews"] / max(1, row["delayed"])) * 100, 1),
            "top_rule": (
                {"rule_id": top_rule[0][0], "count": top_rule[0][1]}
                if top_rule
                else None
            ),
            "top_surface": (
                {"surface": top_surface[0][0], "count": top_surface[0][1]}
                if top_surface
                else None
            ),
        }

    trusted_sources = set(settings.policy_truth_traffic_sources)
    trusted_rows = sum(
        row["claim_created_rows"] for source, row in source_rows.items() if source in trusted_sources
    )
    simulated_rows = total_rows - trusted_rows
    return {
        "trusted_sources": sorted(trusted_sources),
        "source_rows": comparisons,
        "source_contamination": {
            "trusted_rows": trusted_rows,
            "simulated_rows": simulated_rows,
            "trusted_share": round((trusted_rows / max(1, total_rows)) * 100, 1),
            "simulated_share": round((simulated_rows / max(1, total_rows)) * 100, 1),
        },
        "baseline_truth_mode": {
            "enabled": True,
            "sources_used": sorted(trusted_sources),
            "claim_created_rows": trusted_rows,
        },
    }


def _summarize_review_drivers(claims: list[Claim], *, source: str, window_hours: int | None) -> dict:
    driver_counts: dict[str, int] = {}
    seen_incidents: set[str] = set()
    total_incidents = 0
    incident_labels: list[set[str]] = []

    for claim in claims:
        incident_key = _incident_key(claim)
        if incident_key in seen_incidents:
            continue
        seen_incidents.add(incident_key)
        total_incidents += 1
        labels = set(_review_driver_labels(claim))
        incident_labels.append(labels)
        for label in labels:
            driver_counts[label] = driver_counts.get(label, 0) + 1

    drivers = [
        {
            "label": label,
            "count": count,
            "share": round((count / max(1, total_incidents)) * 100),
        }
        for label, count in sorted(driver_counts.items(), key=lambda item: (-item[1], item[0]))
    ][:3]

    return {
        "source": source,
        "window_hours": window_hours,
        "total_incidents": total_incidents,
        "drivers": drivers,
        "insights": _review_insights(driver_counts, incident_labels, total_incidents),
    }


def _build_review_driver_summary(recent_claims: list[Claim], active_queue_claims: list[Claim], recent_window_hours: int) -> dict:
    recent_summary = _summarize_review_drivers(
        recent_claims,
        source="recent_activity",
        window_hours=recent_window_hours,
    )
    if recent_summary["total_incidents"] > 0:
        return recent_summary
    return _summarize_review_drivers(
        active_queue_claims,
        source="active_queue",
        window_hours=None,
    )


@router.get("/admin-overview")
async def get_admin_overview(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    now = utc_now_naive()
    cutoff = now - timedelta(days=days)
    recent_activity_cutoff = now - timedelta(hours=6)
    review_driver_cutoff = now - timedelta(hours=1)

    active_policy_rows = (
        await db.execute(
            select(Policy.plan_name, Policy.weekly_premium, Worker.city)
            .join(Worker, Worker.id == Policy.worker_id)
            .where(
                Policy.status == "active",
                Policy.activates_at <= now,
                Policy.expires_at >= now,
            )
        )
    ).all()

    policies_by_plan: dict[str, int] = {}
    policies_by_city: dict[str, int] = {}
    premiums_in_force = 0.0
    for plan_name, weekly_premium, city in active_policy_rows:
        policies_by_plan[plan_name] = policies_by_plan.get(plan_name, 0) + 1
        if city:
            policies_by_city[city] = policies_by_city.get(city, 0) + 1
        premiums_in_force += float(weekly_premium or 0)

    payouts_total = (
        await db.execute(
            select(func.coalesce(func.sum(Payout.amount), 0)).where(Payout.initiated_at >= cutoff)
        )
    ).scalar_one()
    payouts_total = float(payouts_total or 0)

    recent_claims = (
        await db.execute(select(Claim).where(Claim.created_at >= cutoff))
    ).scalars().all()
    auto_approved_count = 0
    delayed_count = 0
    for claim in recent_claims:
        if claim.status == "delayed":
            delayed_count += 1
        if _is_zero_touch_approved(claim):
            auto_approved_count += 1
    fraud_flagged = sum(1 for claim in recent_claims if float(claim.fraud_score or 0) >= 0.4)
    claim_total = len(recent_claims)
    recent_review_claims = (
        await db.execute(
            select(Claim)
            .options(selectinload(Claim.event))
            .where(Claim.status == "delayed", Claim.created_at >= review_driver_cutoff)
        )
    ).scalars().all()
    delayed_queue_claims = (
        await db.execute(
            select(Claim)
            .options(selectinload(Claim.event))
            .where(Claim.status == "delayed")
        )
    ).scalars().all()
    decision_logs = (
        await db.execute(
            select(DecisionLog).where(DecisionLog.created_at >= cutoff).order_by(DecisionLog.created_at.desc())
        )
    ).scalars().all()

    active_workers = (
        await db.execute(select(func.count(Worker.id)).where(Worker.status == "active"))
    ).scalar_one()
    recent_activity_points = (
        await db.execute(
            select(func.count(WorkerActivity.id)).where(WorkerActivity.recorded_at >= recent_activity_cutoff)
        )
    ).scalar_one()
    worker_activity_index = round((recent_activity_points / max(1, active_workers)) * 10, 1)

    recent_duplicate_logs = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.created_at >= cutoff,
                AuditLog.action.in_(["duplicate_detected", "event_extended"]),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(12)
        )
    ).scalars().all()

    duplicate_claim_log = [
        {
            "id": str(log.id),
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "details": log.details or {},
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_duplicate_logs
    ]

    active_events_by_city = (
        await db.execute(
            select(Event.city, func.count(Event.id))
            .where(Event.status == "active")
            .group_by(Event.city)
        )
    ).all()
    active_city_counts = {city: count for city, count in active_events_by_city}

    cities = list(settings.CITY_RISK_PROFILES.keys())
    city_forecasts = await asyncio.gather(*[_forecast_city_snapshot(city, 168) for city in cities])

    forecast = []
    for city, city_forecast in zip(cities, city_forecasts):
        base = float(settings.CITY_RISK_PROFILES[city]["base_risk"])
        city_score = round(
            sum(zone["projected_risk"] for zone in city_forecast["zones"]) / max(1, len(city_forecast["zones"])),
            3,
        )
        forecast.append(
            {
                "city": city,
                "base_risk": base,
                "active_incidents": active_city_counts.get(city, 0),
                "projected_risk": city_score,
                "band": forecast_band(city_score),
                "top_zone": city_forecast["zones"][0]["zone"] if city_forecast["zones"] else None,
                "model_version": city_forecast["zones"][0]["model_version"] if city_forecast["zones"] else "rule-based",
            }
        )

    return {
        "period_days": days,
        "active_policies_total": len(active_policy_rows),
        "active_policies_by_plan": policies_by_plan,
        "active_policies_by_city": policies_by_city,
        "premiums_in_force": round(premiums_in_force, 2),
        "payouts_in_window": round(payouts_total, 2),
        "loss_ratio": round((payouts_total / max(1.0, premiums_in_force)) * 100, 1),
        "worker_activity_index": worker_activity_index,
        "duplicate_claim_log": duplicate_claim_log,
        "scheduler": trigger_scheduler.state,
        "decision_health": {
            "claim_total": claim_total,
            "auto_approved": auto_approved_count,
            "auto_approval_rate": round((auto_approved_count / max(1, claim_total)) * 100, 1),
            "zero_touch_approvals": auto_approved_count,
            "zero_touch_rate": round((auto_approved_count / max(1, claim_total)) * 100, 1),
            "review_rate": round((delayed_count / max(1, claim_total)) * 100, 1),
        },
        "fraud_rate": round((fraud_flagged / max(1, claim_total)) * 100, 1),
        "decision_memory_summary": _build_decision_memory_summary(decision_logs),
        "false_review_pattern_summary": _build_false_review_pattern_summary(decision_logs),
        "policy_replay_summary": _build_policy_replay_summary(decision_logs),
        "policy_health_summary": _build_policy_health_summary(decision_logs),
        "source_comparison_summary": _build_source_comparison_summary(decision_logs),
        "review_driver_summary": _build_review_driver_summary(recent_review_claims, delayed_queue_claims, recent_window_hours=1),
        "next_week_forecast": forecast,
    }


@router.get("/forecast")
async def get_forecast(
    city: str,
    horizon: int = 24,
    zone: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    if zone:
        return {
            "forecast": await forecast_engine.forecast_zone(db, city.lower(), zone.lower(), horizon_hours=horizon)
        }
    return {"forecast": await forecast_engine.forecast_city(db, city.lower(), horizon_hours=horizon)}


@router.get("/zone-risk")
async def get_zone_risk(
    city: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    return {"city": city.lower(), "zones": await forecast_engine.zone_risk(db, city.lower())}


@router.get("/models")
async def get_models(
    _: dict = Depends(require_admin_session),
):
    risk_info = risk_model_service.get_model_info()
    fraud_info = fraud_model_service.get_model_info()
    return {
        "models": {
            "risk_model": {
                "status": risk_info.get("status"),
                "version": risk_info.get("version"),
                "trained_at": risk_info.get("trained_at"),
                "r2_score": risk_info.get("metrics", {}).get("r2"),
                "mae": risk_info.get("metrics", {}).get("mae"),
                "rmse": risk_info.get("metrics", {}).get("rmse"),
                "model_type": risk_info.get("model_type"),
                "n_samples": risk_info.get("n_samples"),
                "fallback_used": risk_info.get("fallback_used"),
                "last_error": risk_info.get("last_error"),
            },
            "fraud_model": {
                "status": fraud_info.get("status"),
                "version": fraud_info.get("version"),
                "trained_at": fraud_info.get("trained_at"),
                "roc_auc": fraud_info.get("metrics", {}).get("roc_auc"),
                "average_precision": fraud_info.get("metrics", {}).get("average_precision"),
                "precision": fraud_info.get("metrics", {}).get("precision"),
                "recall": fraud_info.get("metrics", {}).get("recall"),
                "model_type": fraud_info.get("model_type"),
                "n_samples": fraud_info.get("n_samples"),
                "fallback_used": fraud_info.get("fallback_used"),
                "last_error": fraud_info.get("last_error"),
            },
            "forecast_engine": {
                "status": "active",
                "version": "forecast-v1",
                "fallback_active": not risk_model_service.model_available,
            },
        }
    }
