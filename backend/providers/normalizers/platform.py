"""Platform payload normalizer."""

from __future__ import annotations

from backend.providers.base import NormalizedSignalSnapshot, ProviderFetchResult
from backend.providers.normalizers.common import build_normalized_snapshot


def normalize_platform(fetch_result: ProviderFetchResult) -> NormalizedSignalSnapshot:
    normalized_metrics = {
        "orders_per_hour": int(fetch_result.raw_payload.get("orders_per_hour", 0) or 0),
        "normal_avg_orders": int(fetch_result.raw_payload.get("normal_avg_orders", 0) or 0),
        "order_density_drop": float(fetch_result.raw_payload.get("order_density_drop", 0) or 0),
    }
    return build_normalized_snapshot(
        fetch_result,
        normalized_metrics,
        ["orders_per_hour", "normal_avg_orders", "order_density_drop"],
    )

