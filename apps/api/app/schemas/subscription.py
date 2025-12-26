"""Subscription-related schemas"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel


class SubscriptionPlanType(str, Enum):
    """Available subscription plans - legacy naming"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionResponse(BaseModel):
    """Subscription details response"""
    id: UUID
    plan: str
    status: str
    amount: float
    currency: str
    interval: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    identities_limit: int
    api_calls_limit: int
    storage_limit_mb: int

    class Config:
        from_attributes = True


class PlanInfo(BaseModel):
    """Plan information"""
    id: str
    name: str
    price_monthly: float
    price_yearly: float
    identities_limit: int
    api_calls_limit: int
    storage_limit_mb: int
    features: List[str]


class PlansListResponse(BaseModel):
    """List of available plans"""
    plans: List[PlanInfo]


class CreateCheckoutRequest(BaseModel):
    """Request to create checkout session"""
    # Accept both string plan name and enum for backward compatibility
    plan: str  # Will be validated against SubscriptionPlan in endpoint
    interval: str = "month"  # "month" or "year"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Checkout session response"""
    checkout_url: str
    session_id: str


class SubscriptionUsageResponse(BaseModel):
    """Current usage vs limits"""
    usage: dict
    limits: dict
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
