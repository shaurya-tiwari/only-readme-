"""Shared helpers for provider normalization."""

from __future__ import annotations

from typing import Any

from backend.providers.base import NormalizedSignalSnapshot, ProviderFetchResult
from backend.utils.time import utc_now_naive


def build_quality_components(
    captured_at,
    normalized_metrics: dict[str, Any],
    required_fields: list[str],
) -> tuple[float, dict[str, float]]:
    age_seconds = max(0.0, (utc_now_naive() - captured_at).total_seconds())
    freshness_score = max(0.0, 1.0 - min(age_seconds, 300.0) / 300.0)
    present_fields = sum(1 for field in required_fields if normalized_metrics.get(field) is not None)
    field_coverage = round(present_fields / max(1, len(required_fields)), 3)
    provider_success_rate = 1.0
    quality_score = round(
        (0.45 * freshness_score) + (0.35 * field_coverage) + (0.20 * provider_success_rate),
        3,
    )
    breakdown = {
        "freshness_score": round(freshness_score, 3),
        "field_coverage": field_coverage,
        "provider_success_rate": provider_success_rate,
    }
    return quality_score, breakdown


def build_confidence_envelope(
    normalized_metrics: dict[str, Any],
    provider: str,
    captured_at,
    quality_score: float,
    is_fallback: bool,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {}
    for key, value in normalized_metrics.items():
        envelope[key] = {
            "value": value,
            "confidence": quality_score,
            "sources": [provider],
            "fallback_used": is_fallback,
            "captured_at": captured_at.isoformat(),
        }
    return envelope


def build_normalized_snapshot(
    fetch_result: ProviderFetchResult,
    normalized_metrics: dict[str, Any],
    required_fields: list[str],
) -> NormalizedSignalSnapshot:
    quality_score, breakdown = build_quality_components(
        fetch_result.captured_at,
        normalized_metrics,
        required_fields,
    )
    return NormalizedSignalSnapshot(
        signal_type=fetch_result.signal_type,
        provider=fetch_result.provider,
        source_mode=fetch_result.source_mode,
        city=fetch_result.city,
        zone=fetch_result.zone,
        captured_at=fetch_result.captured_at,
        normalized_metrics=normalized_metrics,
        raw_payload=fetch_result.raw_payload,
        quality_score=quality_score,
        quality_breakdown=breakdown,
        confidence_envelope=build_confidence_envelope(
            normalized_metrics,
            fetch_result.provider,
            fetch_result.captured_at,
            quality_score,
            fetch_result.is_fallback,
        ),
        latency_ms=fetch_result.latency_ms,
        is_fallback=fetch_result.is_fallback,
        request_id=fetch_result.request_id,
    )

