"""Deterministic tests for the signal aggregation layer."""

from copy import deepcopy

from backend.core.signal_aggregator import signal_aggregator
from backend.providers.base import NormalizedSignalSnapshot
from backend.utils.time import utc_now_naive


def _snapshot(signal_type: str, metrics: dict, raw_payload: dict) -> NormalizedSignalSnapshot:
    return NormalizedSignalSnapshot(
        signal_type=signal_type,
        provider=f"mock-{signal_type}",
        source_mode="mock",
        city="delhi",
        zone="east_delhi",
        captured_at=utc_now_naive(),
        normalized_metrics=metrics,
        raw_payload=raw_payload,
        quality_score=0.9,
        quality_breakdown={"freshness": 0.9},
        confidence_envelope={},
        latency_ms=0,
        is_fallback=False,
        request_id=f"{signal_type}-1",
    )


def test_signal_aggregator_is_deterministic_and_versioned():
    snapshots = [
        _snapshot("weather", {"rainfall_mm_hr": 42.0, "temperature_c": 36.0}, {"timestamp": "2026-04-03T10:00:00", "scenario": "monsoon"}),
        _snapshot("aqi", {"aqi_value": 188}, {"timestamp": "2026-04-03T10:00:00"}),
        _snapshot("traffic", {"congestion_index": 0.81}, {"timestamp": "2026-04-03T10:00:00", "congestion_index": 0.81}),
        _snapshot("platform", {"order_density_drop": 0.72}, {"timestamp": "2026-04-03T10:00:00", "scenario": "platform_outage"}),
    ]

    first = signal_aggregator.build_zone_snapshot(
        "delhi",
        "east_delhi",
        snapshots,
        source_mode="shadow",
        shadow_diffs=[{"signal_type": "weather", "delta": 0.0}],
    )
    second = signal_aggregator.build_zone_snapshot(
        "delhi",
        "east_delhi",
        deepcopy(snapshots),
        source_mode="shadow",
        shadow_diffs=[{"signal_type": "weather", "delta": 0.0}],
    )

    assert first == second
    assert first["aggregation_version"] == signal_aggregator.VERSION
    assert first["source_mode"] == "shadow"
    assert first["social"] > 0
