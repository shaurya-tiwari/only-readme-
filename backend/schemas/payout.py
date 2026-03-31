"""
Pydantic schemas for payouts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    worker_id: UUID
    worker_name: Optional[str] = None
    amount: float
    channel: str
    transaction_id: Optional[str] = None
    status: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None


class PayoutListResponse(BaseModel):
    total: int
    total_amount: float
    payouts: List[PayoutResponse]


class PayoutSummaryResponse(BaseModel):
    worker_id: UUID
    total_payouts: int
    total_amount: float
    this_week_amount: float
    this_week_count: int
    last_payout: Optional[PayoutResponse] = None
    weekly_history: List[Dict[str, Any]]
