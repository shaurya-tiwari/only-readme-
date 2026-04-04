"""Tests for forecast signal preprocessing."""

from datetime import timedelta
from decimal import Decimal

import pytest

from backend.core.forecast_preprocessor import forecast_preprocessor
from backend.database import async_session_factory
from backend.db.models import SignalSnapshot
from backend.providers.base import NormalizedSignalSnapshot
from backend.utils.time import utc_now_naive


def _current_snapshot(signal_type: str, metrics: dict) -> NormalizedSignalSnapshot:
    now = utc_now_naive()
    return NormalizedSignalSnapshot(
        signal_type=signal_type,
        provider=f"mock-{signal_type}",
        source_mode="mock",
        city="delhi",
        zone="east_delhi",
        captured_at=now,
        normalized_metrics=metrics,
        raw_payload={"timestamp": now.isoformat()},
        quality_score=0.9,
        quality_breakdown={"freshness": 0.9},
        confidence_envelope={},
        latency_ms=0,
        is_fallback=False,
        request_id=f"current-{signal_type}",
    )


@pytest.mark.asyncio
async def test_forecast_preprocessor_gap_fills_and_clips_inputs():
    old_time = utc_now_naive() - timedelta(hours=2)

    async with async_session_factory() as session:
        session.add_all(
            [
                SignalSnapshot(
                    city="delhi",
                    zone="east_delhi",
                    signal_type="weather",
                    provider="mock-weather",
                    source_mode="mock",
                    captured_at=old_time,
                    normalized_metrics={"rainfall_mm_hr": 10.0, "temperature_c": 30.0},
                    raw_payload={"timestamp": old_time.isoformat()},
                    quality_score=Decimal("0.900"),
                    quality_breakdown={"freshness": 0.9},
                    confidence_envelope={},
                    latency_ms=0,
                    is_fallback=False,
                    request_id="hist-weather",
                ),
                SignalSnapshot(
                    city="delhi",
                    zone="east_delhi",
                    signal_type="traffic",
                    provider="mock-traffic",
                    source_mode="mock",
                    captured_at=old_time,
                    normalized_metrics={"congestion_index": 0.4},
                    raw_payload={"timestamp": old_time.isoformat()},
                    quality_score=Decimal("0.900"),
                    quality_breakdown={"freshness": 0.9},
                    confidence_envelope={},
                    latency_ms=0,
                    is_fallback=False,
                    request_id="hist-traffic",
                ),
            ]
        )
        await session.flush()

        cleaned, meta = await forecast_preprocessor.preprocess(
            session,
            "east_delhi",
            {
                "snapshots": [
                    _current_snapshot("weather", {"rainfall_mm_hr": 50.0, "temperature_c": 120.0}),
                    _current_snapshot("aqi", {"aqi_value": 180}),
                    _current_snapshot("traffic", {}),
                    _current_snapshot("platform", {"order_density_drop": 0.55}),
                ]
            },
        )

    assert cleaned["traffic"] == 0.4
    assert cleaned["heat"] == 51.0
    assert cleaned["rain"] == 38.0
    assert cleaned["aqi"] == 180
    assert "traffic" in meta["filled_metrics"]
    assert "heat" in meta["clipped_metrics"]
