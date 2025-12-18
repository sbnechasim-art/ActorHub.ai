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
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import Identity
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

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()


@router.get("/listings", response_model=List[ListingResponse])
async def search_listings(
    query: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    featured: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query(default="popular", enum=["popular", "newest", "price_low", "price_high", "rating"]),
    page: int = Query(default=1, ge=1),
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
    stmt = select(Listing).where(Listing.is_active.is_(True))

    # Apply filters
    if query:
        stmt = stmt.where(
            or_(Listing.title.ilike(f"%{query}%"), Listing.description.ilike(f"%{query}%"))
        )

    if category:
        # Convert to uppercase to match PostgreSQL enum
        category_upper = category.upper()
        stmt = stmt.where(Listing.category == category_upper)

    if featured is True:
        stmt = stmt.where(Listing.is_featured.is_(True))

    if tags:
        tag_list = tags.split(",")
        stmt = stmt.where(Listing.tags.overlap(tag_list))

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

    if not listing or not listing.is_active:
        raise HTTPException(404, "Listing not found")

    # Increment view count
    listing.view_count += 1
    await db.commit()

    return listing


@router.post("/listings", response_model=ListingResponse)
async def create_listing(
    listing_data: ListingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new marketplace listing"""
    # Verify identity ownership
    identity = await db.get(Identity, listing_data.identity_id)
    if not identity:
        raise HTTPException(404, "Identity not found")
    if identity.user_id != current_user.id:
        raise HTTPException(403, "You don't own this identity")
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
        published_at=datetime.utcnow(),
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
    if not listing:
        raise HTTPException(404, "Listing not found")

    # Verify ownership
    identity = await db.get(Identity, listing.identity_id)
    if identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(listing, field, value)

    listing.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(listing)

    return listing


# License Pricing
@router.post("/license/price", response_model=LicensePriceResponse)
async def calculate_license_price(request: LicensePriceRequest, db: AsyncSession = Depends(get_db)):
    """Calculate license price based on parameters"""
    identity = await db.get(Identity, request.identity_id)
    if not identity:
        raise HTTPException(404, "Identity not found")

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


@router.post("/license/purchase", response_model=CheckoutSessionResponse)
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

    **Returns:** Stripe checkout session URL to complete payment
    """
    identity = await db.get(Identity, license_data.identity_id)
    if not identity:
        raise HTTPException(404, "Identity not found")

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
        import structlog
        structlog.get_logger().error("Price calculation failed", error=str(e))
        raise HTTPException(500, "Failed to calculate license price")

    # Create pending license
    license = License(
        identity_id=license_data.identity_id,
        licensee_id=current_user.id,
        license_type=LicenseType(license_data.license_type),
        usage_type=UsageType(license_data.usage_type),
        project_name=license_data.project_name,
        project_description=license_data.project_description,
        allowed_platforms=license_data.allowed_platforms,
        max_impressions=license_data.max_impressions,
        max_outputs=license_data.max_outputs,
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=license_data.duration_days),
        price_usd=price_usd,
        payment_status=PaymentStatus.PENDING,
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
            if not current_user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=current_user.email,
                    name=f"{current_user.full_name or current_user.email}",
                    metadata={"user_id": str(current_user.id)},
                )
                current_user.stripe_customer_id = customer.id
                await db.flush()

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
            # Log error but continue with mock URL for development
            import structlog

            structlog.get_logger().error("Stripe checkout error", error=str(e))
            checkout_url = f"{settings.FRONTEND_URL}/checkout/success?session_id={license.id}"
    else:
        # No Stripe configured - use mock success URL for development
        checkout_url = f"{settings.FRONTEND_URL}/checkout/success?session_id={license.id}"

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
            License.payment_status == PaymentStatus.COMPLETED,
            or_(License.valid_until.is_(None), License.valid_until > datetime.utcnow()),
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

    if not license:
        raise HTTPException(404, "License not found")

    # Check access - either licensee or identity owner can view
    identity = await db.get(Identity, license.identity_id)
    if license.licensee_id != current_user.id and identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    return license


@router.get("/categories")
async def get_categories():
    """Get available marketplace categories (loaded from config)"""
    return {"categories": settings.MARKETPLACE_CATEGORIES}
