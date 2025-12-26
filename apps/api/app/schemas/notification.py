"""Notification-related schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Single notification response"""
    id: UUID
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None
    channel: Optional[str] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List of notifications response"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    # Email notification settings
    email_enabled: bool = True
    email_security: bool = True
    email_billing: bool = True
    email_marketing: bool = False
    # Push notification settings
    push_enabled: bool = True
    # SMS notification settings
    sms_enabled: bool = False
    # Alert preferences
    license_alerts: bool = True
    verification_alerts: bool = True
    weekly_digest: bool = True
