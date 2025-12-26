"""Refund-related schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RefundRequest(BaseModel):
    """Request for a refund"""
    license_id: UUID
    reason: str = Field(..., min_length=10, max_length=1000)


class RefundResponse(BaseModel):
    """Refund response"""
    refund_id: str
    status: str
    amount: float
    currency: str
    message: str


class RefundStatusResponse(BaseModel):
    """Refund status check"""
    refund_id: str
    status: str
    amount: float
    created_at: datetime
    processed_at: Optional[datetime] = None


class RefundEligibility(BaseModel):
    """Refund eligibility status"""
    eligible: bool
    reason: Optional[str] = None
    refund_amount: Optional[float] = None
    processing_time: Optional[str] = None
