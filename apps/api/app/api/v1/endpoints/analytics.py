"""
Analytics Endpoints
Usage, revenue, and performance analytics
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.security import get_current_user
from app.models.identity import Identity, ActorPack, UsageLog
from app.models.marketplace import License, Transaction
from app.models.user import User, UserRole
from app.schemas.analytics import (
    TimeSeriesPoint,
    UsageStats,
    RevenueStats,
    IdentityAnalytics,
    DashboardAnalytics,
)

logger = structlog.get_logger()
router = APIRouter()


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/dashboard", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive dashboard analytics for the user.

    Includes usage stats, revenue, top identities, and trends.
    """
    period_start = utc_now() - timedelta(days=days)
    period_end = utc_now()

    # Get usage stats
    usage = await _get_usage_stats(db, current_user.id, period_start, period_end)

    # Get revenue stats
    revenue = await _get_revenue_stats(db, current_user.id, period_start, period_end)

    # Get top identities
    top_identities = await _get_top_identities(db, current_user.id, period_start, limit=5)

    # Get usage trend
    usage_trend = await _get_usage_trend(db, current_user.id, period_start, period_end)

    # Get revenue trend
    revenue_trend = await _get_revenue_trend(db, current_user.id, period_start, period_end)

    return DashboardAnalytics(
        usage=usage,
        revenue=revenue,
        top_identities=top_identities,
        usage_trend=usage_trend,
        revenue_trend=revenue_trend,
    )


@router.get("/usage")
async def get_usage_analytics(
    days: int = Query(default=30, ge=1, le=365),
    identity_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed usage analytics"""
    period_start = utc_now() - timedelta(days=days)

    query = select(
        UsageLog.action,
        func.count().label("count"),
        func.date(UsageLog.created_at).label("date"),
    ).where(
        UsageLog.requester_id == current_user.id,
        UsageLog.created_at >= period_start,
    )

    if identity_id:
        query = query.where(UsageLog.identity_id == identity_id)

    query = query.group_by(
        UsageLog.action,
        func.date(UsageLog.created_at),
    ).order_by(func.date(UsageLog.created_at))

    result = await db.execute(query)
    rows = result.all()

    # Organize by action type
    usage_by_action = {}
    for row in rows:
        action = row.action
        if action not in usage_by_action:
            usage_by_action[action] = []
        usage_by_action[action].append({
            "date": str(row.date),
            "count": row.count,
        })

    # Get totals
    totals = await db.execute(
        select(
            UsageLog.action,
            func.count().label("total"),
        ).where(
            UsageLog.requester_id == current_user.id,
            UsageLog.created_at >= period_start,
        ).group_by(UsageLog.action)
    )

    return {
        "period_days": days,
        "by_action": usage_by_action,
        "totals": {row.action: row.total for row in totals.all()},
    }


@router.get("/revenue")
async def get_revenue_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed revenue analytics"""
    period_start = utc_now() - timedelta(days=days)

    # Revenue by day
    daily_revenue = await db.execute(
        select(
            func.date(Transaction.created_at).label("date"),
            func.sum(Transaction.amount_usd).label("revenue"),
            func.count().label("transactions"),
        ).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "PURCHASE",
            Transaction.created_at >= period_start,
        ).group_by(
            func.date(Transaction.created_at)
        ).order_by(func.date(Transaction.created_at))
    )

    # Revenue by identity
    revenue_by_identity = await db.execute(
        select(
            Identity.id,
            Identity.display_name,
            func.sum(Transaction.amount_usd).label("revenue"),
            func.count().label("sales"),
        ).join(
            License, License.identity_id == Identity.id
        ).join(
            Transaction, Transaction.license_id == License.id
        ).where(
            Identity.user_id == current_user.id,
            Transaction.type == "PURCHASE",
            Transaction.created_at >= period_start,
        ).group_by(
            Identity.id, Identity.display_name
        ).order_by(func.sum(Transaction.amount_usd).desc())
    )

    return {
        "period_days": days,
        "daily": [
            {
                "date": str(row.date),
                "revenue": float(row.revenue or 0),
                "transactions": row.transactions,
            }
            for row in daily_revenue.all()
        ],
        "by_identity": [
            {
                "identity_id": str(row.id),
                "name": row.display_name,
                "revenue": float(row.revenue or 0),
                "sales": row.sales,
            }
            for row in revenue_by_identity.all()
        ],
    }


@router.get("/identity/{identity_id}")
async def get_identity_analytics(
    identity_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for a specific identity"""
    # Verify ownership
    identity = await db.get(Identity, identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    if identity.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    period_start = utc_now() - timedelta(days=days)

    # Usage stats
    usage_stats = await db.execute(
        select(
            UsageLog.action,
            func.count().label("count"),
        ).where(
            UsageLog.identity_id == identity_id,
            UsageLog.created_at >= period_start,
        ).group_by(UsageLog.action)
    )

    # License stats
    license_stats = await db.execute(
        select(
            func.count().label("total_licenses"),
            func.sum(License.price_usd).label("total_revenue"),
        ).where(
            License.identity_id == identity_id,
            License.created_at >= period_start,
        )
    )
    license_row = license_stats.one()

    # Daily usage trend
    daily_usage = await db.execute(
        select(
            func.date(UsageLog.created_at).label("date"),
            func.count().label("count"),
        ).where(
            UsageLog.identity_id == identity_id,
            UsageLog.created_at >= period_start,
        ).group_by(
            func.date(UsageLog.created_at)
        ).order_by(func.date(UsageLog.created_at))
    )

    return {
        "identity_id": str(identity_id),
        "identity_name": identity.display_name,
        "period_days": days,
        "usage_by_action": {row.action: row.count for row in usage_stats.all()},
        "licenses_sold": license_row.total_licenses or 0,
        "total_revenue": float(license_row.total_revenue or 0),
        "daily_usage": [
            {"date": str(row.date), "count": row.count}
            for row in daily_usage.all()
        ],
    }


@router.get("/admin/platform")
async def get_platform_analytics(
    days: int = Query(default=30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide analytics (admin only)"""
    period_start = utc_now() - timedelta(days=days)

    # Total users
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    new_users = await db.scalar(
        select(func.count()).where(User.created_at >= period_start)
    ) or 0

    # Total identities
    total_identities = await db.scalar(
        select(func.count()).where(Identity.deleted_at.is_(None))
    ) or 0
    new_identities = await db.scalar(
        select(func.count()).where(
            Identity.created_at >= period_start,
            Identity.deleted_at.is_(None),
        )
    ) or 0

    # Total revenue
    total_revenue = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(Transaction.type == "PURCHASE")
    ) or 0
    period_revenue = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(
            Transaction.type == "PURCHASE",
            Transaction.created_at >= period_start,
        )
    ) or 0

    # API calls
    total_api_calls = await db.scalar(select(func.count()).select_from(UsageLog)) or 0
    period_api_calls = await db.scalar(
        select(func.count()).where(UsageLog.created_at >= period_start)
    ) or 0

    # Daily active users
    dau = await db.execute(
        select(
            func.date(UsageLog.created_at).label("date"),
            func.count(func.distinct(UsageLog.requester_id)).label("users"),
        ).where(
            UsageLog.created_at >= period_start
        ).group_by(
            func.date(UsageLog.created_at)
        ).order_by(func.date(UsageLog.created_at))
    )

    return {
        "period_days": days,
        "users": {
            "total": total_users,
            "new": new_users,
        },
        "identities": {
            "total": total_identities,
            "new": new_identities,
        },
        "revenue": {
            "total": float(total_revenue),
            "period": float(period_revenue),
            "currency": "USD",
        },
        "api_calls": {
            "total": total_api_calls,
            "period": period_api_calls,
        },
        "daily_active_users": [
            {"date": str(row.date), "users": row.users}
            for row in dau.all()
        ],
    }


# Helper functions

async def _get_usage_stats(
    db: AsyncSession,
    user_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> UsageStats:
    """Get usage statistics for a user"""
    result = await db.execute(
        select(
            UsageLog.action,
            func.count().label("count"),
        ).where(
            UsageLog.requester_id == user_id,
            UsageLog.created_at >= period_start,
            UsageLog.created_at <= period_end,
        ).group_by(UsageLog.action)
    )

    counts = {row.action: row.count for row in result.all()}

    return UsageStats(
        total_verifications=counts.get("verify", 0) + counts.get("VERIFY", 0),
        total_generations=counts.get("generate", 0) + counts.get("GENERATE", 0),
        total_api_calls=sum(counts.values()),
        period_start=period_start,
        period_end=period_end,
    )


async def _get_revenue_stats(
    db: AsyncSession,
    user_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> RevenueStats:
    """Get revenue statistics for a user"""
    # Income from sales
    revenue = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(
            Transaction.user_id == user_id,
            Transaction.type == "PURCHASE",
            Transaction.created_at >= period_start,
        )
    ) or 0

    # Payouts received
    payouts = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(
            Transaction.user_id == user_id,
            Transaction.type == "PAYOUT",
            Transaction.created_at >= period_start,
        )
    ) or 0

    # Transaction count
    txn_count = await db.scalar(
        select(func.count()).where(
            Transaction.user_id == user_id,
            Transaction.created_at >= period_start,
        )
    ) or 0

    return RevenueStats(
        total_revenue=float(revenue),
        total_payouts=float(payouts),
        net_earnings=float(revenue) - float(payouts),
        transaction_count=txn_count,
        currency="USD",
    )


async def _get_top_identities(
    db: AsyncSession,
    user_id: UUID,
    period_start: datetime,
    limit: int = 5,
) -> List[IdentityAnalytics]:
    """Get top performing identities - optimized with single query"""
    # Create subqueries for license stats to avoid N+1 queries
    license_stats = (
        select(
            License.identity_id,
            func.count(License.id).label("license_count"),
            func.coalesce(func.sum(License.price_usd), 0).label("total_revenue"),
        )
        .group_by(License.identity_id)
        .subquery()
    )

    # Single query with all data
    result = await db.execute(
        select(
            Identity.id,
            Identity.display_name,
            func.count(UsageLog.id).label("usage_count"),
            func.coalesce(license_stats.c.license_count, 0).label("licenses_sold"),
            func.coalesce(license_stats.c.total_revenue, 0).label("revenue"),
        )
        .outerjoin(UsageLog, UsageLog.identity_id == Identity.id)
        .outerjoin(license_stats, license_stats.c.identity_id == Identity.id)
        .where(
            Identity.user_id == user_id,
            Identity.deleted_at.is_(None),
        )
        .group_by(
            Identity.id,
            Identity.display_name,
            license_stats.c.license_count,
            license_stats.c.total_revenue,
        )
        .order_by(func.count(UsageLog.id).desc())
        .limit(limit)
    )

    return [
        IdentityAnalytics(
            identity_id=row.id,
            identity_name=row.display_name or "Unnamed",
            verifications=row.usage_count,
            generations=0,  # Would need action type filtering
            licenses_sold=row.licenses_sold,
            revenue=float(row.revenue),
        )
        for row in result.all()
    ]


async def _get_usage_trend(
    db: AsyncSession,
    user_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> List[TimeSeriesPoint]:
    """Get daily usage trend"""
    result = await db.execute(
        select(
            func.date(UsageLog.created_at).label("date"),
            func.count().label("count"),
        ).where(
            UsageLog.requester_id == user_id,
            UsageLog.created_at >= period_start,
            UsageLog.created_at <= period_end,
        ).group_by(
            func.date(UsageLog.created_at)
        ).order_by(func.date(UsageLog.created_at))
    )

    return [
        TimeSeriesPoint(date=str(row.date), value=float(row.count))
        for row in result.all()
    ]


async def _get_revenue_trend(
    db: AsyncSession,
    user_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> List[TimeSeriesPoint]:
    """Get daily revenue trend"""
    result = await db.execute(
        select(
            func.date(Transaction.created_at).label("date"),
            func.sum(Transaction.amount_usd).label("amount"),
        ).where(
            Transaction.user_id == user_id,
            Transaction.type == "PURCHASE",
            Transaction.created_at >= period_start,
            Transaction.created_at <= period_end,
        ).group_by(
            func.date(Transaction.created_at)
        ).order_by(func.date(Transaction.created_at))
    )

    return [
        TimeSeriesPoint(date=str(row.date), value=float(row.amount or 0))
        for row in result.all()
    ]
