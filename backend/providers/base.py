"""Shared provider contracts and normalized signal payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ProviderFetchResult:
    signal_type: str
    provider: str
    source_mode: str
    city: str
    zone: str
    captured_at: datetime
    raw_payload: dict[str, Any]
    latency_ms: int = 0
    is_fallback: bool = False
    request_id: str | None = None


@dataclass(slots=True)
class NormalizedSignalSnapshot:
    signal_type: str
    provider: str
    source_mode: str
    city: str
    zone: str
    captured_at: datetime
    normalized_metrics: dict[str, Any]
    raw_payload: dict[str, Any]
    quality_score: float
    quality_breakdown: dict[str, float]
    confidence_envelope: dict[str, Any]
    latency_ms: int = 0
    is_fallback: bool = False
    request_id: str | None = None


class SignalProvider(Protocol):
    """Provider interface for a single signal source."""

    signal_type: str
    source_name: str

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        """Fetch a raw provider payload for the requested zone."""

