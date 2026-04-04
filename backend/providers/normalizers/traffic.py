"""Traffic payload normalizer."""

from __future__ import annotations

from backend.providers.base import NormalizedSignalSnapshot, ProviderFetchResult
from backend.providers.normalizers.common import build_normalized_snapshot


def normalize_traffic(fetch_result: ProviderFetchResult) -> NormalizedSignalSnapshot:
    normalized_metrics = {
        "congestion_index": float(fetch_result.raw_payload.get("congestion_index", 0) or 0),
    }
    return build_normalized_snapshot(fetch_result, normalized_metrics, ["congestion_index"])

