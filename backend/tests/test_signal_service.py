"""Tests for the signal service migration layer."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.config import settings
from backend.core.shadow_diff_writer import shadow_diff_writer
from backend.core.signal_service import signal_service
from backend.core.snapshot_writer import snapshot_writer
from backend.database import async_session_factory
from backend.db.models import ShadowSignalDiff, SignalSnapshot
from backend.utils.time import utc_now_naive


@pytest.mark.asyncio
async def test_signal_service_persists_normalized_snapshots():
    async with async_session_factory() as session:
        payload = await signal_service.fetch_zone_snapshot(session, "south_delhi", "delhi")
        snapshots = (await session.execute(select(SignalSnapshot))).scalars().all()

    assert payload["city"] == "delhi"
    assert payload["zone"] == "south_delhi"
    assert payload["source_mode"] == "mock"
    assert payload["rain"] >= 0
    assert payload["aqi"] >= 0
    assert set(payload["sources"].keys()) == {"weather", "aqi", "traffic", "platform"}
    assert len(snapshots) == 4
    assert {snapshot.signal_type for snapshot in snapshots} == {"weather", "aqi", "traffic", "platform"}
    assert all(snapshot.quality_score is not None for snapshot in snapshots)


@pytest.mark.asyncio
async def test_signal_service_shadow_mode_returns_structured_diffs():
    async with async_session_factory() as session:
        payload = await signal_service.fetch_zone_snapshot(session, "east_delhi", "delhi", mode="shadow")

    assert len(payload["shadow_diffs"]) == 4
    assert {diff["signal_type"] for diff in payload["shadow_diffs"]} == {"weather", "aqi", "traffic", "platform"}
    assert all("metric_deltas" in diff for diff in payload["shadow_diffs"])
    assert all(diff["delta"] == 0.0 for diff in payload["shadow_diffs"])
    assert all("requires_attention" in diff for diff in payload["shadow_diffs"])


@pytest.mark.asyncio
async def test_signal_service_persists_shadow_diffs_and_prunes_stale_records(monkeypatch):
    monkeypatch.setattr(settings, "SIGNAL_RETENTION_CLEANUP_INTERVAL", 1)
    monkeypatch.setattr(settings, "SIGNAL_SNAPSHOT_RETENTION_DAYS", 7)
    monkeypatch.setattr(settings, "SHADOW_DIFF_RETENTION_DAYS", 7)
    snapshot_writer._writes_since_cleanup = 0
    shadow_diff_writer._writes_since_cleanup = 0
    stale_time = utc_now_naive() - timedelta(days=30)

    async with async_session_factory() as session:
        session.add(
            SignalSnapshot(
                city="delhi",
                zone="east_delhi",
                signal_type="weather",
                provider="stale-provider",
                source_mode="mock",
                captured_at=stale_time,
                normalized_metrics={"rainfall_mm_hr": 5.0},
                raw_payload={"timestamp": stale_time.isoformat()},
                quality_score=Decimal("0.800"),
                quality_breakdown={"freshness": 0.8},
                confidence_envelope={"rainfall_mm_hr": {"value": 5.0, "confidence": 0.8}},
                latency_ms=0,
                is_fallback=False,
                request_id="stale-snapshot",
            )
        )
        session.add(
            ShadowSignalDiff(
                city="delhi",
                zone="east_delhi",
                signal_type="weather",
                primary_provider="mock-weather",
                shadow_provider="mock-weather",
                compared_at=stale_time,
                max_delta=Decimal("0.100"),
                metric_deltas={"rainfall_mm_hr": {"primary": 1.0, "shadow": 1.1, "delta": 0.1}},
                threshold_crossed=False,
                alert_triggered=False,
                threshold_state={"primary": False, "shadow": False},
            )
        )
        await session.flush()

        await signal_service.fetch_zone_snapshot(session, "east_delhi", "delhi", mode="shadow")

        snapshots = (await session.execute(select(SignalSnapshot))).scalars().all()
        diffs = (await session.execute(select(ShadowSignalDiff))).scalars().all()

    assert len(snapshots) == 4
    assert {snapshot.signal_type for snapshot in snapshots} == {"weather", "aqi", "traffic", "platform"}
    assert len(diffs) == 4
    assert {diff.signal_type for diff in diffs} == {"weather", "aqi", "traffic", "platform"}
