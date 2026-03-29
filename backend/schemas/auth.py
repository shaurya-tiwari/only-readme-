"""
Schemas for lightweight Sprint 3 auth/session endpoints.
"""

from pydantic import BaseModel, Field


class WorkerLoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)


class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=3, max_length=100)
