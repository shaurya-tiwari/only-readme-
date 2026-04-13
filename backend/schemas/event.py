"""
Pydantic schemas for disruption events and trigger checks.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    zone: str
    city: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    severity: Optional[float] = None
    raw_value: Optional[float] = None
    threshold: Optional[float] = None
    disruption_score: Optional[float] = None
    event_confidence: Optional[float] = None
    api_source: Optional[str] = None
    status: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    duration_hours: Optional[float] = None
    claims_generated: int = 0


class EventListResponse(BaseModel):
    total: int
    active_count: int
    events: List[EventResponse]


class TriggerCheckRequest(BaseModel):
    """Request to manually run a trigger cycle."""

    zones: Optional[List[str]] = None
    scenario: Optional[str] = Field(
        None,
        description=(
            "Force a scenario: heavy_rain, extreme_heat, hazardous_aqi, "
            "monsoon, platform_outage, compound_disaster"
        ),
    )
    city: str = Field(default="delhi")
    demo_run_id: Optional[str] = Field(
        default=None,
        description="Simulation-only run identifier to force a fresh demo incident.",
    )


class TriggerCheckResponse(BaseModel):
    zones_checked: List[str]
    triggers_fired: Dict[str, List[str]]
    events_created: int
    events_extended: int
    claims_generated: int
    claims_approved: int
    claims_delayed: int
    claims_rejected: int
    total_payout: float
    details: List[Dict[str, Any]]


class LabSignalConfig(BaseModel):
    rain_mm_hr: float = 0
    temperature_c: float = 30
    aqi_value: int = 120
    congestion_index: float = 0.35
    order_density_drop: float = 0.1


class LabWorkerConfig(BaseModel):
    seed_demo_worker: bool = True
    profile: str = Field(default="legit", pattern="^(legit|edge|fraud)$")
    plan_name: str = "smart_protect"
    platform: str = "zomato"
    self_reported_income: int = 900
    working_hours: int = 8


class LabExecutionConfig(BaseModel):
    mode: str = Field(default="single", pattern="^(single|batch)$")
    runs: int = Field(default=1, ge=1, le=20)


class TriggerLabRequest(BaseModel):
    city: str = Field(default="delhi")
    zones: List[str] = Field(default_factory=list)
    signals: LabSignalConfig = Field(default_factory=LabSignalConfig)
    worker: LabWorkerConfig = Field(default_factory=LabWorkerConfig)
    execution: LabExecutionConfig = Field(default_factory=LabExecutionConfig)
    preset_name: Optional[str] = None


class SignalSnapshot(BaseModel):
    """Current signal readings for a zone."""

    zone: str
    timestamp: str
    rain_mm_hr: float
    temperature_c: float
    aqi_value: int
    congestion_index: float
    order_density_drop: float
    normalized_inactivity: float
    triggers_active: List[str]
