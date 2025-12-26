"""Admin-related schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics"""
    total_users: int
    active_users: int
    total_identities: int
    total_actor_packs: int = 0
    verified_identities: int = 0
    total_revenue: float
    revenue_this_month: float = 0.0
    pending_payouts: float = 0.0
    total_verifications: int = 0
    api_calls_today: int = 0
    active_subscriptions: int = 0
    system_health: str = "healthy"


class UserSummary(BaseModel):
    """User summary for admin views"""
    id: UUID
    email: str
    display_name: Optional[str] = None
    role: str
    tier: str
    is_active: bool
    identities_count: int = 0
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    created_at: datetime


class SystemMetrics(BaseModel):
    """System metrics for monitoring"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    request_rate: float
    error_rate: float
    avg_response_time_ms: int


class UserListResponse(BaseModel):
    """Paginated list of users for admin"""
    users: List[UserSummary]
    total: int
    limit: int
    offset: int


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs"""
    logs: List[AuditLogEntry]
    total: int
    limit: int
    offset: int
