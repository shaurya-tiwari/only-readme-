"""
Pydantic schemas for claims.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    worker_id: UUID
    worker_name: Optional[str] = None
    policy_id: UUID
    event_id: UUID
    trigger_type: str
    disruption_hours: Optional[float] = None
    income_per_hour: Optional[float] = None
    peak_multiplier: Optional[float] = None
    calculated_payout: Optional[float] = None
    final_payout: Optional[float] = None
    disruption_score: Optional[float] = None
    event_confidence: Optional[float] = None
    fraud_score: Optional[float] = None
    trust_score: Optional[float] = None
    final_score: Optional[float] = None
    decision_breakdown: Optional[Dict[str, Any]] = None
    status: str
    rejection_reason: Optional[str] = None
    review_deadline: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    is_overdue: Optional[bool] = None
    fraud_probability: Optional[float] = None
    payout_risk: Optional[float] = None
    hours_waiting: Optional[float] = None
    hours_until_deadline: Optional[float] = None
    overdue_hours: Optional[float] = None
    urgency_score: Optional[float] = None
    urgency_band: Optional[str] = None
    priority_reason: Optional[str] = None
    decision_confidence: Optional[float] = None
    decision_confidence_band: Optional[str] = None
    primary_factor: Optional[str] = None
    secondary_factors: Optional[List[str]] = None
    payout_info: Optional[Dict[str, Any]] = None


class ClaimListResponse(BaseModel):
    total: int
    approved: int
    delayed: int
    rejected: int
    total_payout: float
    claims: List[ClaimResponse]


class ClaimResolveRequest(BaseModel):
    """Admin resolving a delayed claim."""

    decision: str = Field(
        ...,
        description="approve or reject",
        pattern="^(approve|reject)$",
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for rejection (required if rejecting)",
    )
    reviewed_by: str = Field(
        default="admin",
        description="Admin identifier",
    )


class ReviewQueueResponse(BaseModel):
    total_pending: int
    overdue_count: int
    high_load_mode: Optional[bool] = None
    high_load_threshold: Optional[int] = None
    claims: List[ClaimResponse]


class ClaimExplainResponse(BaseModel):
    """Full explanation of why a claim was approved, delayed, or rejected."""

    claim_id: UUID
    status: str
    final_score: float
    decision_explanation: str
    signal_breakdown: Dict[str, Any]
    fraud_signals: Dict[str, Any]
    worker_activity_summary: Dict[str, Any]
    event_summary: Dict[str, Any]
