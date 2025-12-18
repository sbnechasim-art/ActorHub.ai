"""
Notification Endpoints
User notification management
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notifications import Notification, NotificationType, NotificationChannel
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response schema"""
    id: UUID
    type: str
    title: str
    message: str
    action_url: Optional[str] = None
    channel: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List of notifications with pagination"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email_security: bool = True
    email_billing: bool = True
    email_marketing: bool = False
    push_enabled: bool = True
    sms_enabled: bool = False


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    is_read: Optional[bool] = None,
    type: Optional[NotificationType] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user notifications with optional filtering"""
    query = select(Notification).where(Notification.user_id == current_user.id)

    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    if type:
        query = query.where(Notification.type == type)

    query = query.order_by(Notification.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get unread count
    unread_query = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                type=n.type.value if n.type else "SYSTEM",
                title=n.title,
                message=n.message,
                action_url=n.action_url,
                channel=n.channel.value if n.channel else "IN_APP",
                is_read=n.is_read or False,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications"""
    query = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    result = await db.execute(query)
    count = result.scalar() or 0

    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read"""
    notification = await db.get(Notification, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()

    return {"status": "success", "message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read"""
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.execute(stmt)
    await db.commit()

    return {"status": "success", "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification"""
    notification = await db.get(Notification, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(notification)
    await db.commit()

    return {"status": "success", "message": "Notification deleted"}


@router.get("/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
):
    """Get user's notification preferences"""
    prefs = current_user.notification_settings or {}

    return NotificationPreferences(
        email_security=prefs.get("email_security", True),
        email_billing=prefs.get("email_billing", True),
        email_marketing=prefs.get("email_marketing", False),
        push_enabled=prefs.get("push_enabled", True),
        sms_enabled=prefs.get("sms_enabled", False),
    )


@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's notification preferences"""
    current_user.notification_settings = preferences.model_dump()
    await db.commit()

    return {"status": "success", "message": "Preferences updated"}
