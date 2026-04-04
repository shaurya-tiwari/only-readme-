"""Weather payload normalizer."""

from __future__ import annotations

from backend.providers.base import NormalizedSignalSnapshot, ProviderFetchResult
from backend.providers.normalizers.common import build_normalized_snapshot


def normalize_weather(fetch_result: ProviderFetchResult) -> NormalizedSignalSnapshot:
    normalized_metrics = {
        "rainfall_mm_hr": float(fetch_result.raw_payload.get("rainfall_mm_hr", 0) or 0),
        "temperature_c": float(fetch_result.raw_payload.get("temperature_c", 0) or 0),
    }
    return build_normalized_snapshot(fetch_result, normalized_metrics, ["rainfall_mm_hr", "temperature_c"])

