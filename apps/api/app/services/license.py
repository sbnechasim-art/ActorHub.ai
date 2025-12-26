"""
License Service
Business logic for license and marketplace operations

Encapsulates:
- License pricing calculation
- License purchase workflow
- Refund processing
- Listing management
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime


def escape_like_pattern(value: str) -> str:
    """
    Escape special characters for SQL LIKE patterns.

    SECURITY FIX: Prevents LIKE pattern injection where users could
    manipulate search behavior using % (any chars) or _ (single char).

    Args:
        value: User input to be used in LIKE pattern

    Returns:
        Escaped string safe for use in LIKE patterns
    """
    # Escape the escape character first, then special LIKE chars
    value = value.replace("\\", "\\\\")
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")
    return value

from app.core.config import settings
from app.models.identity import Identity
from app.models.marketplace import License, Listing, Transaction, LicenseType, UsageType, PaymentStatus
from app.models.user import User

logger = structlog.get_logger()


class LicenseService:
    """Service for license and marketplace operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===========================================
    # Price Calculation
    # ===========================================

    async def calculate_license_price(
        self,
        identity_id: UUID,
        license_type: str,
        usage_type: str,
        duration_days: int,
    ) -> Dict[str, Any]:
        """
        Calculate license price based on parameters.

        Returns:
            Price breakdown including base, multipliers, and total
        """
        identity = await self.db.get(Identity, identity_id)
        if not identity:
            raise ValueError("Identity not found")

        # Base price from identity
        base_price = identity.base_license_fee or 99

        # Duration multiplier
        if duration_days <= 7:
            duration_multiplier = 0.3
        elif duration_days <= 30:
            duration_multiplier = 1.0
        elif duration_days <= 90:
            duration_multiplier = 2.5
        elif duration_days <= 365:
            duration_multiplier = 8.0
        else:
            duration_multiplier = 10.0

        # Usage type multiplier
        usage_multipliers = {
            "COMMERCIAL": 3.0,
            "EDITORIAL": 1.5,
            "EDUCATIONAL": 0.5,
            "PERSONAL": 1.0,
        }
        usage_multiplier = usage_multipliers.get(usage_type.upper(), 1.0)

        # Calculate totals
        subtotal = base_price * duration_multiplier * usage_multiplier
        platform_fee = subtotal * 0.20  # 20% platform fee
        total_price = subtotal + platform_fee

        return {
            "base_price": base_price,
            "duration_multiplier": duration_multiplier,
            "usage_multiplier": usage_multiplier,
            "platform_fee": round(platform_fee, 2),
            "total_price": round(total_price, 2),
            "breakdown": {
                "base": base_price,
                "duration_adjustment": round(base_price * (duration_multiplier - 1), 2),
                "usage_adjustment": round(base_price * duration_multiplier * (usage_multiplier - 1), 2),
                "platform_fee": round(platform_fee, 2),
            },
        }

    # ===========================================
    # License Purchase
    # ===========================================

    async def create_pending_license(
        self,
        identity_id: UUID,
        licensee: User,
        license_type: str,
        usage_type: str,
        duration_days: int,
        project_name: Optional[str] = None,
        project_description: Optional[str] = None,
        allowed_platforms: Optional[List[str]] = None,
        max_impressions: Optional[int] = None,
        max_outputs: Optional[int] = None,
    ) -> tuple[License, float]:
        """
        Create a pending license for purchase.

        Returns:
            Tuple of (License, price_usd)
        """
        identity = await self.db.get(Identity, identity_id)
        if not identity:
            raise ValueError("Identity not found")

        if not identity.allow_commercial_use:
            raise ValueError("This identity does not allow commercial use")

        # Calculate price
        price_info = await self.calculate_license_price(
            identity_id=identity_id,
            license_type=license_type,
            usage_type=usage_type,
            duration_days=duration_days,
        )
        price_usd = price_info["total_price"]

        # Create pending license
        license = License(
            identity_id=identity_id,
            licensee_id=licensee.id,
            license_type=license_type.upper(),
            usage_type=usage_type.upper(),
            project_name=project_name,
            project_description=project_description,
            allowed_platforms=allowed_platforms,
            max_impressions=max_impressions,
            max_outputs=max_outputs,
            valid_from=utc_now(),
            valid_until=utc_now() + timedelta(days=duration_days),
            price_usd=price_usd,
            payment_status="PENDING",
            creator_payout_usd=price_usd * 0.80,  # 80% to creator
        )
        self.db.add(license)
        await self.db.flush()

        logger.info(
            "Pending license created",
            license_id=str(license.id),
            identity_id=str(identity_id),
            licensee_id=str(licensee.id),
            price_usd=price_usd,
        )

        return license, price_usd

    async def activate_license(self, license_id: UUID, payment_intent_id: str) -> License:
        """Activate a license after payment confirmation"""
        license = await self.db.get(License, license_id)
        if not license:
            raise ValueError("License not found")

        license.payment_status = "COMPLETED"
        license.is_active = True
        license.stripe_payment_intent_id = payment_intent_id
        license.paid_at = utc_now()

        await self.db.commit()
        await self.db.refresh(license)

        logger.info(
            "License activated",
            license_id=str(license_id),
            payment_intent_id=payment_intent_id,
        )

        return license

    # ===========================================
    # Refund Processing
    # ===========================================

    async def check_refund_eligibility(
        self,
        license: License,
        user: User,
    ) -> Dict[str, Any]:
        """
        Check if a license is eligible for refund.

        Returns:
            Eligibility status and reason
        """
        # Check if already refunded
        if license.payment_status == "REFUNDED":
            return {"eligible": False, "reason": "License already refunded"}

        # Check refund window
        purchase_date = license.created_at
        refund_window = timedelta(days=settings.REFUND_WINDOW_DAYS)
        if utc_now() - purchase_date > refund_window:
            return {
                "eligible": False,
                "reason": f"Refund window expired. Refunds must be requested within {settings.REFUND_WINDOW_DAYS} days.",
            }

        # Prevent immediate refund abuse
        min_age = timedelta(hours=settings.REFUND_COOLING_HOURS)
        if utc_now() - purchase_date < min_age:
            return {
                "eligible": False,
                "reason": f"Please wait at least {settings.REFUND_COOLING_HOURS} hour(s) after purchase.",
            }

        # Check user's refund history
        refund_count = await self.db.scalar(
            select(func.count()).where(
                Transaction.user_id == user.id,
                Transaction.type == "REFUND",
            )
        ) or 0

        if refund_count >= settings.MAX_REFUNDS_PER_USER:
            return {
                "eligible": False,
                "reason": f"Maximum refund limit ({settings.MAX_REFUNDS_PER_USER}) reached.",
            }

        return {"eligible": True, "reason": None}

    async def process_refund(
        self,
        license: License,
        user: User,
        reason: str,
        stripe_refund_id: str,
    ) -> Transaction:
        """
        Process a refund for a license.

        Returns:
            Refund transaction record
        """
        # Get original transaction
        original_transaction = await self.db.scalar(
            select(Transaction).where(
                Transaction.license_id == license.id,
                Transaction.type == "PURCHASE",
            )
        )

        if not original_transaction:
            raise ValueError("Original transaction not found")

        # Update license status
        license.payment_status = "REFUNDED"
        license.is_active = False

        # Create refund transaction
        refund_transaction = Transaction(
            user_id=user.id,
            license_id=license.id,
            type="REFUND",
            amount_usd=-original_transaction.amount_usd,
            currency=original_transaction.currency,
            stripe_payment_intent_id=stripe_refund_id,
            status="COMPLETED",
            transaction_metadata={
                "original_transaction_id": str(original_transaction.id),
                "refund_reason": reason,
            },
        )
        self.db.add(refund_transaction)
        await self.db.commit()

        logger.info(
            "Refund processed",
            license_id=str(license.id),
            refund_id=stripe_refund_id,
            amount=original_transaction.amount_usd,
        )

        return refund_transaction

    # ===========================================
    # License Queries
    # ===========================================

    async def get_user_licenses(
        self,
        user: User,
        active_only: bool = False,
    ) -> List[License]:
        """Get all licenses purchased by a user"""
        query = select(License).where(License.licensee_id == user.id)

        if active_only:
            query = query.where(
                License.is_active.is_(True),
                License.payment_status == "COMPLETED",
                or_(
                    License.valid_until.is_(None),
                    License.valid_until > utc_now(),
                ),
            )

        query = query.order_by(License.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_license(self, license_id: UUID) -> Optional[License]:
        """Get a license by ID"""
        return await self.db.get(License, license_id)

    # ===========================================
    # Listing Management
    # ===========================================

    async def search_listings(
        self,
        query_text: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        featured: Optional[bool] = None,
        sort_by: str = "popular",
        page: int = 1,
        limit: int = 20,
    ) -> List[Listing]:
        """Search marketplace listings"""
        stmt = select(Listing).where(Listing.is_active.is_(True))

        # Apply filters
        if query_text:
            # SECURITY FIX: Escape special LIKE characters to prevent pattern injection
            safe_query = escape_like_pattern(query_text)
            stmt = stmt.where(
                or_(
                    Listing.title.ilike(f"%{safe_query}%", escape="\\"),
                    Listing.description.ilike(f"%{safe_query}%", escape="\\"),
                )
            )

        if category:
            stmt = stmt.where(Listing.category == category.upper())

        if featured is True:
            stmt = stmt.where(Listing.is_featured.is_(True))

        if tags:
            stmt = stmt.where(Listing.tags.overlap(tags))

        # Sorting
        if sort_by == "newest":
            stmt = stmt.order_by(Listing.created_at.desc())
        elif sort_by == "rating":
            stmt = stmt.order_by(Listing.avg_rating.desc().nullslast())
        else:  # popular
            stmt = stmt.order_by(Listing.view_count.desc())

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_listing(
        self,
        identity: Identity,
        title: str,
        description: str,
        category: str,
        pricing_tiers: List[Dict[str, Any]],
        short_description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        requires_approval: bool = False,
    ) -> Listing:
        """Create a new marketplace listing"""
        import uuid

        if not identity.allow_commercial_use:
            raise ValueError("Identity must allow commercial use to be listed")

        # Generate slug
        slug = title.lower().replace(" ", "-")[:50]
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        listing = Listing(
            identity_id=identity.id,
            title=title,
            slug=slug,
            description=description,
            short_description=short_description,
            category=category.upper(),
            tags=tags or [],
            pricing_tiers=pricing_tiers,
            requires_approval=requires_approval,
            thumbnail_url=identity.profile_image_url,
            preview_images=[],
            published_at=utc_now(),
        )
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)

        logger.info(
            "Listing created",
            listing_id=str(listing.id),
            identity_id=str(identity.id),
        )

        return listing

    async def get_listing(self, listing_id: UUID) -> Optional[Listing]:
        """Get a listing by ID"""
        listing = await self.db.get(Listing, listing_id)
        if listing and listing.is_active:
            # Increment view count
            listing.view_count += 1
            await self.db.commit()
        return listing


# ===========================================
# Dependency for FastAPI
# ===========================================

async def get_license_service(db: AsyncSession) -> LicenseService:
    """FastAPI dependency for LicenseService"""
    return LicenseService(db)
