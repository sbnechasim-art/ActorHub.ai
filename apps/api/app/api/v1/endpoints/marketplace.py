"""
Marketplace API Endpoints

This module handles all marketplace functionality including:
- Browsing and searching listings
- License pricing calculation
- License purchasing via Stripe
- License management
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import Identity
from app.services.user import UserService
from app.services.license import escape_like_pattern
from app.models.marketplace import (
    License,
    LicenseType,
    Listing,
    PaymentStatus,
    UsageType,
)
from app.models.user import User
from app.schemas.marketplace import (
    CheckoutSessionResponse,
    LicenseCreate,
    LicensePriceRequest,
    LicensePriceResponse,
    LicenseResponse,
    ListingCreate,
    ListingResponse,
    ListingUpdate,
)
from app.core.helpers import get_or_404, check_ownership, get_owned_or_404

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = structlog.get_logger()
router = APIRouter()


@router.get("/listings", response_model=List[ListingResponse])
async def search_listings(
    # SECURITY FIX: Added length limits and validation to prevent DoS attacks
    query: Optional[str] = Query(default=None, max_length=200, description="Search query (max 200 chars)"),
    category: Optional[str] = Query(default=None, max_length=50, regex="^[a-zA-Z0-9_-]+$", description="Category filter"),
    tags: Optional[str] = Query(default=None, max_length=500, description="Comma-separated tags (max 500 chars)"),
    featured: Optional[bool] = None,
    min_price: Optional[float] = Query(default=None, ge=0, le=1000000, description="Minimum price (0-1M)"),
    max_price: Optional[float] = Query(default=None, ge=0, le=1000000, description="Maximum price (0-1M)"),
    sort_by: str = Query(default="popular", regex="^(popular|newest|price_low|price_high|rating)$"),
    page: int = Query(default=1, ge=1, le=500, description="Page number (max 500)"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Search marketplace listings.

    Browse available identities in the marketplace. This is a public endpoint
    that does not require authentication.

    **Filters:**
    - `query`: Search in title and description
    - `category`: Filter by category (actor, model, influencer, etc.)
    - `tags`: Comma-separated list of tags
    - `featured`: Filter to featured listings only
    - `min_price` / `max_price`: Price range filter

    **Sorting options:**
    - `popular`: Most viewed listings (default)
    - `newest`: Recently added
    - `price_low`: Lowest price first
    - `price_high`: Highest price first
    - `rating`: Highest rated first
    """
    # MEDIUM FIX: Use eager loading to prevent N+1 queries
    stmt = select(Listing).options(
        selectinload(Listing.identity)
    ).where(Listing.is_active.is_(True))

    # Apply filters
    if query:
        # SECURITY FIX: Escape LIKE pattern special characters
        safe_query = escape_like_pattern(query)
        stmt = stmt.where(
            or_(
                Listing.title.ilike(f"%{safe_query}%", escape="\\"),
                Listing.description.ilike(f"%{safe_query}%", escape="\\")
            )
        )

    if category:
        # Convert to uppercase to match PostgreSQL enum
        category_upper = category.upper()
        stmt = stmt.where(Listing.category == category_upper)

    if featured is True:
        stmt = stmt.where(Listing.is_featured.is_(True))

    if tags:
        # SECURITY: Limit number of tags to prevent array DoS
        tag_list = [t.strip()[:50] for t in tags.split(",")[:20]]  # Max 20 tags, 50 chars each
        tag_list = [t for t in tag_list if t]  # Remove empty tags
        if tag_list:
            stmt = stmt.where(Listing.tags.overlap(tag_list))

    # SECURITY FIX: Price range validation and filtering
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise HTTPException(
                status_code=400,
                detail="min_price cannot be greater than max_price"
            )
    if min_price is not None:
        stmt = stmt.where(Listing.base_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.base_price <= max_price)

    # Sorting
    if sort_by == "newest":
        stmt = stmt.order_by(Listing.created_at.desc())
    elif sort_by == "price_low":
        stmt = stmt.order_by(Listing.pricing_tiers[0]["price"].asc())
    elif sort_by == "price_high":
        stmt = stmt.order_by(Listing.pricing_tiers[0]["price"].desc())
    elif sort_by == "rating":
        stmt = stmt.order_by(Listing.avg_rating.desc().nullslast())
    else:  # popular
        stmt = stmt.order_by(Listing.view_count.desc())

    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific listing"""
    listing = await db.get(Listing, listing_id)

    # Treat inactive listings as not found
    if listing and not listing.is_active:
        listing = None

    listing = get_or_404(listing, "Listing", listing_id)

    # Increment view count
    listing.view_count += 1
    await db.commit()

    return listing


@router.post("/listings", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    listing_data: ListingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new marketplace listing.

    **Returns:** 201 Created with listing details.

    **Errors:**
    - 400: Identity must allow commercial use
    - 401: Unauthorized
    - 403: You don't own this identity
    - 404: Identity not found
    """
    # Verify identity ownership
    identity = await db.get(Identity, listing_data.identity_id)
    identity = get_owned_or_404(identity, current_user.id, "Identity")

    if not identity.allow_commercial_use:
        raise HTTPException(400, "Identity must allow commercial use to be listed")

    # Generate slug
    slug = listing_data.title.lower().replace(" ", "-")[:50]
    slug = f"{slug}-{str(uuid.uuid4())[:8]}"

    # Convert category to uppercase to match PostgreSQL enum
    category_value = listing_data.category.upper() if listing_data.category else None

    listing = Listing(
        identity_id=listing_data.identity_id,
        title=listing_data.title,
        slug=slug,
        description=listing_data.description,
        short_description=listing_data.short_description,
        category=category_value,
        tags=listing_data.tags,
        pricing_tiers=listing_data.pricing_tiers,
        requires_approval=listing_data.requires_approval,
        thumbnail_url=identity.profile_image_url,
        preview_images=[],
        published_at=utc_now(),
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)

    return listing


@router.patch("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: uuid.UUID,
    update_data: ListingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a listing"""
    listing = await db.get(Listing, listing_id)
    listing = get_or_404(listing, "Listing", listing_id)

    # Verify ownership via identity
    identity = await db.get(Identity, listing.identity_id)
    check_ownership(identity, current_user.id, entity_name="listing")

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(listing, field, value)

    listing.updated_at = utc_now()
    await db.commit()
    await db.refresh(listing)

    return listing


# License Pricing
@router.post("/license/price", response_model=LicensePriceResponse)
async def calculate_license_price(request: LicensePriceRequest, db: AsyncSession = Depends(get_db)):
    """Calculate license price based on parameters"""
    identity = await db.get(Identity, request.identity_id)
    identity = get_or_404(identity, "Identity", request.identity_id)

    # Base price from identity
    base_price = identity.base_license_fee or 99

    # Duration multiplier
    duration_multiplier = 1.0
    if request.duration_days <= 7:
        duration_multiplier = 0.3
    elif request.duration_days <= 30:
        duration_multiplier = 1.0
    elif request.duration_days <= 90:
        duration_multiplier = 2.5
    elif request.duration_days <= 365:
        duration_multiplier = 8.0

    # Usage type multiplier
    usage_multiplier = 1.0
    if request.usage_type == UsageType.COMMERCIAL.value:
        usage_multiplier = 3.0
    elif request.usage_type == UsageType.EDITORIAL.value:
        usage_multiplier = 1.5
    elif request.usage_type == UsageType.EDUCATIONAL.value:
        usage_multiplier = 0.5

    # Calculate totals
    subtotal = base_price * duration_multiplier * usage_multiplier
    platform_fee = subtotal * 0.20  # 20% platform fee
    total_price = subtotal + platform_fee

    return LicensePriceResponse(
        base_price=base_price,
        duration_multiplier=duration_multiplier,
        usage_multiplier=usage_multiplier,
        platform_fee=platform_fee,
        total_price=round(total_price, 2),
        breakdown={
            "base": base_price,
            "duration_adjustment": round(base_price * (duration_multiplier - 1), 2),
            "usage_adjustment": round(base_price * duration_multiplier * (usage_multiplier - 1), 2),
            "platform_fee": round(platform_fee, 2),
        },
    )


@router.post("/license/purchase", response_model=CheckoutSessionResponse, status_code=status.HTTP_201_CREATED)
async def purchase_license(
    license_data: LicenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Purchase a license to use a protected identity.

    Creates a pending license and returns a Stripe checkout URL for payment.
    The license will be activated automatically when payment is confirmed via webhook.

    **License Types:**
    - `standard`: Basic usage rights
    - `extended`: Additional distribution rights
    - `exclusive`: Exclusive usage rights

    **Usage Types:**
    - `personal`: Non-commercial personal projects
    - `editorial`: News and educational content
    - `commercial`: Commercial advertising and marketing
    - `educational`: Educational materials

    **Returns:** 201 Created with Stripe checkout session URL to complete payment.

    **Errors:**
    - 401: Unauthorized
    - 403: Identity does not allow commercial use
    - 404: Identity not found
    - 500: Failed to calculate license price
    """
    identity = await db.get(Identity, license_data.identity_id)
    identity = get_or_404(identity, "Identity", license_data.identity_id)

    if not identity.allow_commercial_use:
        raise HTTPException(403, "This identity does not allow commercial use")

    # Calculate price
    try:
        price_request = LicensePriceRequest(
            identity_id=license_data.identity_id,
            license_type=license_data.license_type,
            usage_type=license_data.usage_type,
            duration_days=license_data.duration_days,
        )
        price_response = await calculate_license_price(price_request, db)
        price_usd = price_response.total_price
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Price calculation failed", error=str(e))
        raise HTTPException(500, "Failed to calculate license price")

    # Create pending license
    license = License(
        identity_id=license_data.identity_id,
        licensee_id=current_user.id,
        license_type=license_data.license_type.upper(),
        usage_type=license_data.usage_type.upper(),
        project_name=license_data.project_name,
        project_description=license_data.project_description,
        allowed_platforms=license_data.allowed_platforms,
        max_impressions=license_data.max_impressions,
        max_outputs=license_data.max_outputs,
        valid_from=utc_now(),
        valid_until=utc_now() + timedelta(days=license_data.duration_days),
        price_usd=price_usd,
        payment_status="PENDING",
        creator_payout_usd=price_usd * 0.80,  # 80% to creator
    )
    db.add(license)
    await db.flush()

    # Create Stripe checkout session
    checkout_url = None
    session_id = str(license.id)

    if settings.STRIPE_SECRET_KEY:
        try:
            # Ensure user has Stripe customer ID
            user_service = UserService(db)
            await user_service.ensure_stripe_customer(current_user)

            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=current_user.stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": int(price_usd * 100),  # Stripe uses cents
                            "product_data": {
                                "name": f"{identity.display_name} - {license_data.license_type.title()} License",
                                "description": f"{license_data.usage_type.title()} use for {license_data.duration_days} days",
                                "images": (
                                    [identity.profile_image_url]
                                    if identity.profile_image_url
                                    else []
                                ),
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/checkout?canceled=true",
                metadata={
                    "license_id": str(license.id),
                    "identity_id": str(license_data.identity_id),
                    "user_id": str(current_user.id),
                },
            )
            checkout_url = checkout_session.url
            session_id = checkout_session.id
            license.stripe_payment_intent_id = checkout_session.payment_intent
        except stripe.error.StripeError as e:
            logger.error("Stripe checkout error", error=str(e))
            if settings.DEBUG:
                # Development fallback - skip payment
                checkout_url = f"{settings.FRONTEND_URL}/checkout/success?session_id={license.id}&dev_mode=true"
            else:
                raise HTTPException(500, "Payment processing error. Please try again.")
    else:
        if settings.DEBUG:
            # Development mode without Stripe - skip payment
            checkout_url = f"{settings.FRONTEND_URL}/checkout/success?session_id={license.id}&dev_mode=true"
        else:
            raise HTTPException(503, "Payment system not configured")

    await db.commit()

    return CheckoutSessionResponse(
        checkout_url=checkout_url,
        session_id=session_id,
        price_usd=price_usd,
        license_details={
            "identity_name": identity.display_name,
            "license_type": license_data.license_type,
            "usage_type": license_data.usage_type,
            "duration_days": license_data.duration_days,
        },
    )


@router.get("/licenses/mine", response_model=List[LicenseResponse])
async def get_my_licenses(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all licenses purchased by current user"""
    stmt = select(License).where(License.licensee_id == current_user.id)

    if active_only:
        stmt = stmt.where(
            License.is_active.is_(True),
            License.payment_status == "COMPLETED",
            or_(License.valid_until.is_(None), License.valid_until > utc_now()),
        )

    stmt = stmt.order_by(License.created_at.desc())
    result = await db.execute(stmt)

    return result.scalars().all()


@router.get("/licenses/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific license"""
    license = await db.get(License, license_id)
    license = get_or_404(license, "License", license_id)

    # Check access - either licensee or identity owner can view
    identity = await db.get(Identity, license.identity_id)
    if license.licensee_id != current_user.id and identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    return license


@router.delete("/licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_license(
    license_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke/cancel a license.

    Only the identity owner can revoke licenses for their identity.
    Licensees should request a refund instead.

    **Returns:** 204 No Content on success.

    **Errors:**
    - 400: Cannot revoke paid license (use refund), or license already inactive
    - 401: Unauthorized
    - 403: Only identity owner can revoke licenses
    - 404: License not found
    """
    license = await db.get(License, license_id)
    license = get_or_404(license, "License", license_id)

    # Get identity to check ownership
    identity = await db.get(Identity, license.identity_id)
    if not identity or identity.user_id != current_user.id:
        raise HTTPException(403, "Only the identity owner can revoke licenses")

    # Check if already inactive
    if not license.is_active:
        raise HTTPException(400, "License is already inactive")

    # For paid licenses, recommend refund instead
    if license.payment_status == "COMPLETED" and license.price_usd and license.price_usd > 0:
        raise HTTPException(
            400,
            "Cannot revoke a paid license. The licensee should request a refund via /api/v1/refunds/request"
        )

    # Revoke the license
    license.is_active = False
    license.revoked_at = utc_now()
    license.revoked_by = current_user.id

    await db.commit()
    logger.info("License revoked", license_id=str(license_id), by_user=str(current_user.id))


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    listing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete/deactivate a marketplace listing.

    This soft-deletes the listing (sets is_active=False).
    Existing licenses remain valid until expiration.

    **Returns:** 204 No Content on success.

    **Errors:**
    - 401: Unauthorized
    - 403: You don't own this listing
    - 404: Listing not found
    """
    listing = await db.get(Listing, listing_id)
    listing = get_or_404(listing, "Listing", listing_id)

    # Verify ownership via identity
    identity = await db.get(Identity, listing.identity_id)
    if not identity or identity.user_id != current_user.id:
        raise HTTPException(403, "You don't own this listing")

    # Soft delete
    listing.is_active = False
    listing.updated_at = utc_now()

    await db.commit()
    logger.info("Listing deactivated", listing_id=str(listing_id), by_user=str(current_user.id))


@router.get("/categories")
async def get_categories():
    """Get available marketplace categories (loaded from config)"""
    return {"categories": settings.MARKETPLACE_CATEGORIES}
