"""
Users API Endpoints
User management and API keys
"""

import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_api_key,
    get_current_user,
    hash_api_key,
    hash_password,
    verify_password,
)
from app.models.user import ApiKey, User
from app.schemas.user import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    LoginRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
async def register_user(
    request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)
):
    """Register a new user account"""
    # Check if email exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password) if user_data.password else None,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        display_name=user_data.display_name or user_data.email.split("@")[0],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send welcome email (non-blocking)
    try:
        from app.services.email import get_email_service
        email_service = get_email_service()
        await email_service.send_welcome_email(
            to_email=user.email,
            name=user.display_name or user.first_name or "there",
        )
    except Exception as e:
        # Don't fail registration if email fails
        import structlog
        logger = structlog.get_logger()
        logger.warning(f"Failed to send welcome email: {e}")

    return user


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get access token"""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(401, "Account is inactive")

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 15 * 60,  # 15 minutes in seconds
        "user": UserResponse.model_validate(user),
    }


@router.post("/refresh")
@limiter.limit("5/minute")
async def refresh_token(request: Request, refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using a valid refresh token.
    Returns new access and refresh tokens.
    Rate limited to 5 requests per minute to prevent token refresh bomb attacks.
    """
    payload = decode_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(401, "Invalid or expired refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token payload")

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(401, "User not found")

    if not user.is_active:
        raise HTTPException(401, "Account is inactive")

    # Create new tokens
    token_data = {"sub": str(user.id), "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 15 * 60,
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# Allowed fields that users can update on their own profile
ALLOWED_USER_UPDATE_FIELDS = {
    "first_name",
    "last_name",
    "display_name",
    "avatar_url",
    "phone_number",
    "preferences",
    "notification_settings",
    "consent_marketing",
    "consent_analytics",
    "consent_third_party",
    "consent_ai_training",
}


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user information"""
    update_dict = update_data.model_dump(exclude_unset=True)

    # Only allow updating specific fields (security: prevent role/tier escalation)
    for field, value in update_dict.items():
        if field not in ALLOWED_USER_UPDATE_FIELDS:
            raise HTTPException(400, f"Field '{field}' cannot be modified")
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.get("/me/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for current user"""
    from sqlalchemy import func

    from app.models.identity import Identity
    from app.models.marketplace import License

    # Count identities
    identities_query = select(func.count(Identity.id)).where(
        Identity.user_id == current_user.id, Identity.deleted_at.is_(None)
    )
    identities_result = await db.execute(identities_query)
    identities_count = identities_result.scalar()

    # Sum revenue
    revenue_query = select(func.coalesce(func.sum(Identity.total_revenue), 0)).where(
        Identity.user_id == current_user.id
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = revenue_result.scalar()

    # Sum verifications
    verifications_query = select(func.coalesce(func.sum(Identity.total_verifications), 0)).where(
        Identity.user_id == current_user.id
    )
    verifications_result = await db.execute(verifications_query)
    total_verifications = verifications_result.scalar()

    # Count active licenses (simplified query to avoid enum casting issues)
    try:
        licenses_query = (
            select(func.count(License.id))
            .join(Identity)
            .where(Identity.user_id == current_user.id, License.is_active.is_(True))
        )
        licenses_result = await db.execute(licenses_query)
        licenses_count = licenses_result.scalar() or 0
    except Exception:
        licenses_count = 0

    return {
        "identities_count": identities_count or 0,
        "total_revenue": float(total_revenue or 0),
        "verification_checks": int(total_verifications or 0),
        "active_licenses": licenses_count,
        "user_tier": current_user.tier.value,
    }


# API Keys Management
@router.post("/api-keys", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key.

    **Note:** The full API key is only shown once. Store it securely.
    """
    # Generate key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    # Calculate expiry
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Create record
    api_key = ApiKey(
        user_id=current_user.id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        permissions=key_data.permissions,
        rate_limit=key_data.rate_limit,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreatedResponse(api_key=raw_key, key_info=ApiKeyResponse.model_validate(api_key))


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List all API keys for current user"""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an API key"""
    api_key = await db.get(ApiKey, key_id)

    if not api_key:
        raise HTTPException(404, "API key not found")

    if api_key.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    api_key.is_active = False
    await db.commit()

    return {"message": "API key revoked successfully"}


# ==========================================
# Stripe Connect Onboarding (For Creator Payouts)
# ==========================================

@router.post("/connect/onboarding")
async def create_connect_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Stripe Connect onboarding link for creator payouts.

    This initiates the Stripe Connect Express onboarding flow where
    users can set up their payout account to receive earnings from
    their licensed identities.

    Returns:
        - url: Onboarding URL to redirect user to
        - account_id: Stripe Connect account ID
    """
    import stripe
    from app.core.config import settings

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Check if user already has a Connect account
        if current_user.stripe_connect_account_id:
            # Check account status
            account = stripe.Account.retrieve(current_user.stripe_connect_account_id)

            if account.details_submitted:
                return {
                    "status": "complete",
                    "account_id": current_user.stripe_connect_account_id,
                    "message": "Stripe Connect account already set up"
                }

            # Account exists but onboarding incomplete - create new link
            account_link = stripe.AccountLink.create(
                account=current_user.stripe_connect_account_id,
                refresh_url=f"{settings.FRONTEND_URL}/dashboard/settings?connect=refresh",
                return_url=f"{settings.FRONTEND_URL}/dashboard/settings?connect=success",
                type="account_onboarding",
            )

            return {
                "status": "pending",
                "url": account_link.url,
                "account_id": current_user.stripe_connect_account_id,
            }

        # Create new Connect Express account
        account = stripe.Account.create(
            type="express",
            country="US",  # Default, can be changed in onboarding
            email=current_user.email,
            capabilities={
                "transfers": {"requested": True},
            },
            business_type="individual",
            metadata={
                "user_id": str(current_user.id),
                "email": current_user.email,
            },
        )

        # Save account ID to user
        current_user.stripe_connect_account_id = account.id
        await db.commit()

        # Create onboarding link
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"{settings.FRONTEND_URL}/dashboard/settings?connect=refresh",
            return_url=f"{settings.FRONTEND_URL}/dashboard/settings?connect=success",
            type="account_onboarding",
        )

        return {
            "status": "created",
            "url": account_link.url,
            "account_id": account.id,
        }

    except stripe.error.StripeError as e:
        raise HTTPException(400, f"Stripe error: {str(e)}")


@router.get("/connect/status")
async def get_connect_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current Stripe Connect account status.

    Returns:
        - connected: Whether user has a Connect account
        - details_submitted: Whether onboarding is complete
        - payouts_enabled: Whether account can receive payouts
        - account_id: Stripe Connect account ID (if exists)
    """
    import stripe
    from app.core.config import settings

    if not current_user.stripe_connect_account_id:
        return {
            "connected": False,
            "details_submitted": False,
            "payouts_enabled": False,
            "account_id": None,
        }

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        account = stripe.Account.retrieve(current_user.stripe_connect_account_id)

        return {
            "connected": True,
            "details_submitted": account.details_submitted,
            "payouts_enabled": account.payouts_enabled,
            "charges_enabled": account.charges_enabled,
            "account_id": current_user.stripe_connect_account_id,
            "requirements": account.requirements.currently_due if account.requirements else [],
        }

    except stripe.error.StripeError as e:
        raise HTTPException(400, f"Stripe error: {str(e)}")


@router.post("/connect/dashboard")
async def create_connect_dashboard_link(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a link to the Stripe Connect Express dashboard.

    This allows users to manage their payout settings, view
    transaction history, and update bank account details.
    """
    import stripe
    from app.core.config import settings

    if not current_user.stripe_connect_account_id:
        raise HTTPException(400, "No Stripe Connect account found. Complete onboarding first.")

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        login_link = stripe.Account.create_login_link(
            current_user.stripe_connect_account_id
        )

        return {
            "url": login_link.url,
        }

    except stripe.error.StripeError as e:
        raise HTTPException(400, f"Stripe error: {str(e)}")


@router.get("/payout-settings")
async def get_payout_settings(
    current_user: User = Depends(get_current_user),
):
    """
    Get user's payout settings and balance.
    """
    import stripe
    from app.core.config import settings

    result = {
        "connect_status": "not_connected",
        "balance": {"available": 0, "pending": 0, "currency": "usd"},
        "payout_schedule": None,
    }

    if not current_user.stripe_connect_account_id:
        return result

    if not settings.STRIPE_SECRET_KEY:
        return result

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        account = stripe.Account.retrieve(current_user.stripe_connect_account_id)

        if not account.details_submitted:
            result["connect_status"] = "incomplete"
            return result

        if not account.payouts_enabled:
            result["connect_status"] = "pending_verification"
            return result

        result["connect_status"] = "active"

        # Get balance
        balance = stripe.Balance.retrieve(
            stripe_account=current_user.stripe_connect_account_id
        )

        # Sum available and pending amounts (handle multiple currencies)
        available = sum(b.amount for b in balance.available) / 100 if balance.available else 0
        pending = sum(b.amount for b in balance.pending) / 100 if balance.pending else 0
        currency = balance.available[0].currency if balance.available else "usd"

        result["balance"] = {
            "available": available,
            "pending": pending,
            "currency": currency,
        }

        # Get payout schedule
        if account.settings and account.settings.payouts:
            result["payout_schedule"] = {
                "interval": account.settings.payouts.schedule.interval,
                "delay_days": account.settings.payouts.schedule.delay_days,
            }

        return result

    except stripe.error.StripeError:
        return result
