"""
Pydantic schemas for Worker API.
Handles request validation and response serialization.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================
# REQUEST SCHEMAS
# ============================================

class WorkerRegisterRequest(BaseModel):
    """Schema for worker registration."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full name of the delivery worker",
        examples=["Rahul Kumar"]
    )
    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Phone number with country code",
        examples=["+919876543210"]
    )
    city: str = Field(
        ...,
        description="City where worker operates",
        examples=["delhi"]
    )
    zone: Optional[str] = Field(
        None,
        description="Specific zone within the city",
        examples=["south_delhi"]
    )
    platform: str = Field(
        ...,
        description="Delivery platform",
        examples=["zomato"]
    )
    self_reported_income: float = Field(
        ...,
        gt=0,
        le=5000,
        description="Self-reported daily income in INR",
        examples=[900]
    )
    working_hours: float = Field(
        ...,
        gt=0,
        le=18,
        description="Average working hours per day",
        examples=[9]
    )
    consent_given: bool = Field(
        ...,
        description="Worker consents to location tracking for claim validation"
    )

    @field_validator("city")
    @classmethod
    def validate_city(cls, v):
        valid_cities = ["delhi", "mumbai", "bengaluru", "chennai"]
        v_lower = v.lower().strip()
        if v_lower not in valid_cities:
            raise ValueError(f"City must be one of: {', '.join(valid_cities)}")
        return v_lower

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v):
        valid_platforms = ["zomato", "swiggy", "dunzo", "blinkit"]
        v_lower = v.lower().strip()
        if v_lower not in valid_platforms:
            raise ValueError(f"Platform must be one of: {', '.join(valid_platforms)}")
        return v_lower

    @field_validator("consent_given")
    @classmethod
    def validate_consent(cls, v):
        if not v:
            raise ValueError(
                "Consent is required. RideShield uses location data "
                "for claim validation and fraud prevention."
            )
        return v


class WorkerUpdateRequest(BaseModel):
    """Schema for updating worker details."""

    zone: Optional[str] = None
    self_reported_income: Optional[float] = Field(None, gt=0, le=5000)
    working_hours: Optional[float] = Field(None, gt=0, le=18)


# ============================================
# RESPONSE SCHEMAS
# ============================================

class RiskScoreBreakdown(BaseModel):
    """Breakdown of how risk score was calculated."""

    city_base_risk: float
    seasonal_factor: float
    zone_modifier: float
    final_risk_score: float
    risk_level: str
    explanation: str


class PlanOption(BaseModel):
    """A single plan option with calculated premium."""

    plan_name: str
    display_name: str
    weekly_premium: int
    coverage_cap: int
    triggers_covered: List[str]
    description: str
    color: str
    is_recommended: bool = False


class WorkerRegisterResponse(BaseModel):
    """Response after successful registration."""

    worker_id: UUID
    name: str
    city: str
    zone: Optional[str]
    platform: str
    risk_score: float
    risk_breakdown: RiskScoreBreakdown
    available_plans: List[PlanOption]
    recommended_plan: str
    activation_delay_hours: int
    message: str

    model_config = ConfigDict(from_attributes=True)


class WorkerProfileResponse(BaseModel):
    """Full worker profile response."""

    id: UUID
    name: str
    phone: str
    city: str
    zone: Optional[str]
    platform: str
    self_reported_income: Optional[float]
    working_hours: Optional[float]
    risk_score: Optional[float]
    status: str
    consent_given: bool
    created_at: datetime
    trust_score: Optional[float] = None
    active_policy: Optional[dict] = None
    total_claims: int = 0
    total_payouts: float = 0

    model_config = ConfigDict(from_attributes=True)


class WorkerListResponse(BaseModel):
    """Response for listing workers (admin)."""

    total: int
    workers: List[WorkerProfileResponse]
