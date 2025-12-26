"""Analytics-related schemas"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TimeSeriesPoint(BaseModel):
    """A single data point in a time series"""
    date: str
    value: float


class UsageStats(BaseModel):
    """Usage statistics"""
    total_verifications: int
    total_matches: int = 0
    total_generations: int = 0
    total_api_calls: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: int = 0
    period_days: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class RevenueStats(BaseModel):
    """Revenue statistics"""
    total_revenue: float
    total_payouts: float
    pending_balance: float = 0.0
    net_earnings: float = 0.0
    license_count: int = 0
    transaction_count: int = 0
    avg_license_price: float = 0.0
    currency: str = "USD"


class IdentityAnalytics(BaseModel):
    """Analytics for a single identity"""
    identity_id: UUID
    identity_name: str  # Alias for display_name for compatibility
    display_name: Optional[str] = None
    verifications: int = 0
    generations: int = 0
    total_verifications: int = 0
    total_matches: int = 0
    total_revenue: float = 0.0
    license_count: int = 0
    licenses_sold: int = 0
    revenue: float = 0.0


class DashboardAnalytics(BaseModel):
    """Full dashboard analytics"""
    usage: UsageStats
    revenue: RevenueStats
    # Support both naming conventions for backward compatibility
    usage_trend: List[TimeSeriesPoint] = []
    revenue_trend: List[TimeSeriesPoint] = []
    verification_history: List[TimeSeriesPoint] = []
    revenue_history: List[TimeSeriesPoint] = []
    top_identities: List[IdentityAnalytics] = []
