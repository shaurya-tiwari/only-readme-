"""
Pydantic schemas for Policy API.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.schemas.worker import PlanOption


# ============================================
# REQUEST SCHEMAS
# ============================================

class PolicyCreateRequest(BaseModel):
    """Schema for purchasing a weekly plan."""

    worker_id: UUID = Field(
        ...,
        description="Worker who is purchasing the plan"
    )
    plan_name: str = Field(
        ...,
        description="Plan identifier",
        examples=["smart_protect"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_name": "smart_protect"
            }
        }
    )


# ============================================
# RESPONSE SCHEMAS
# ============================================

class PremiumCalculation(BaseModel):
    """Shows how premium was calculated."""

    base_price: float
    plan_factor: float
    risk_score: float
    raw_premium: float
    final_premium: int
    formula: str


class PolicyResponse(BaseModel):
    """Single policy response."""

    id: UUID
    worker_id: UUID
    plan_name: str
    plan_display_name: str
    weekly_premium: float
    coverage_cap: float
    triggers_covered: List[str]
    status: str
    purchased_at: datetime
    activates_at: datetime
    expires_at: datetime
    is_active: bool = False
    premium_calculation: Optional[PremiumCalculation] = None

    model_config = ConfigDict(from_attributes=True)


class PolicyCreateResponse(BaseModel):
    """Response after purchasing a plan."""

    policy: PolicyResponse
    premium_calculation: PremiumCalculation
    message: str
    activation_note: str


class PlanListResponse(BaseModel):
    """All available plans with premiums calculated for a worker."""

    worker_id: UUID
    risk_score: float
    plans: List[PlanOption]
    recommended: str


class PolicyHistoryResponse(BaseModel):
    """Worker's policy history."""

    worker_id: UUID
    total_policies: int
    total_premiums_paid: float
    policies: List[PolicyResponse]
