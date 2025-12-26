"""
Users API Endpoints
User management and API keys
"""

import uuid
from datetime import datetime, timedelta
from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime

logger = structlog.get_logger()
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_2fa_pending_token,
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
    DashboardStats,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    StatusResponse,
    TokenResponse,
    TwoFactorPendingResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from typing import Union

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_user(
    request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.

    **Returns:** 201 Created with user details on success.

    **Errors:**
    - 400: Email already registered
    - 422: Validation error (weak password, invalid email)
    - 429: Rate limit exceeded
    """
    # Check if email exists (exclude soft-deleted)
    existing = await db.execute(
        select(User).where(User.email == user_data.email, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    # Clean up soft-deleted user with same email
    deleted_result = await db.execute(
        select(User).where(User.email == user_data.email, User.deleted_at.isnot(None))
    )
    deleted_user = deleted_result.scalar_one_or_none()
    if deleted_user:
        await db.delete(deleted_user)
        await db.flush()

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


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly cookies for authentication tokens."""
    # Access token cookie (shorter expiry)
    response.set_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_NAME,
        value=access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )
    # Refresh token cookie (longer expiry)
    response.set_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies on logout."""
    response.delete_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_NAME,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )
    response.delete_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_NAME,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


@router.post("/login", response_model=Union[TokenResponse, TwoFactorPendingResponse])
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login and get access token.

    **Returns:**
    - If 2FA disabled: Access token, refresh token, and user details
    - If 2FA enabled: pending_token to complete 2FA verification

    Tokens are also set as httpOnly cookies for security.

    **Errors:**
    - 401: Invalid credentials or inactive account
    - 429: Rate limit exceeded

    **SECURITY NOTE:** When 2FA is enabled, this endpoint returns a
    short-lived pending_token instead of the full access token.
    The user must call /auth/2fa/verify-login with this token to complete login.
    """
    result = await db.execute(
        select(User).where(User.email == credentials.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(401, "Account is inactive")

    # SECURITY FIX: Check if 2FA is enabled
    if user.is_2fa_enabled and user.totp_secret:
        # Return a pending token instead of full access
        # This token proves the user passed password auth and is valid for 5 minutes
        pending_token = create_2fa_pending_token(str(user.id))

        return {
            "requires_2fa": True,
            "pending_token": pending_token,
            "message": "Two-factor authentication required",
        }

    # No 2FA - proceed with normal login
    # Update last login
    user.last_login_at = utc_now()
    await db.commit()

    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Set httpOnly cookies (secure - not accessible via JavaScript)
    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse.model_validate(user),
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
@limiter.limit("5/minute")
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    refresh_token: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using a valid refresh token.

    The refresh token can be provided in the request body or will be
    automatically read from httpOnly cookies.

    Returns new access and refresh tokens (also set as httpOnly cookies).
    Rate limited to 5 requests per minute to prevent token refresh bomb attacks.

    **Errors:**
    - 401: Invalid or expired refresh token, user not found, or inactive account
    - 429: Rate limit exceeded
    """
    # Try to get refresh token from cookies if not in body
    token = refresh_token
    if not token:
        token = request.cookies.get(settings.COOKIE_REFRESH_TOKEN_NAME)

    if not token:
        raise HTTPException(401, "No refresh token provided")

    payload = decode_refresh_token(token)
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

    # Set httpOnly cookies
    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """
    Logout user by clearing authentication cookies.

    **Returns:** Success message.

    This endpoint clears the httpOnly cookies that store the access
    and refresh tokens. No authentication required - just clears cookies.
    """
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


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

    current_user.updated_at = utc_now()
    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.get("/me/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get dashboard statistics for current user.

    **Returns:** Identity count, revenue, verifications, licenses, and tier.

    **Errors:**
    - 401: Unauthorized
    """
    from sqlalchemy import func

    from app.models.identity import Identity
    from app.models.marketplace import License

    # OPTIMIZED: Single query for all identity stats (was 3 separate queries)
    identity_stats_query = select(
        func.count(Identity.id).filter(Identity.deleted_at.is_(None)).label("count"),
        func.coalesce(func.sum(Identity.total_revenue), 0).label("revenue"),
        func.coalesce(func.sum(Identity.total_verifications), 0).label("verifications"),
    ).where(Identity.user_id == current_user.id)

    identity_result = await db.execute(identity_stats_query)
    identity_stats = identity_result.one()

    identities_count = identity_stats.count or 0
    total_revenue = identity_stats.revenue or 0
    total_verifications = identity_stats.verifications or 0

    # Count active licenses (separate query due to JOIN)
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

    return DashboardStats(
        identities_count=identities_count,
        total_revenue=float(total_revenue),
        verification_checks=int(total_verifications),
        active_licenses=licenses_count,
        user_tier=getattr(current_user.tier, 'value', None) or current_user.tier or "FREE",
    )


# API Keys Management
@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key.

    **Note:** The full API key is only shown once. Store it securely.

    **Returns:** 201 Created with API key details.

    **Errors:**
    - 401: Unauthorized
    - 422: Validation error
    """
    # Generate key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    # Calculate expiry
    expires_at = None
    if key_data.expires_in_days:
        expires_at = utc_now() + timedelta(days=key_data.expires_in_days)

    # Create record
    api_key = ApiKey(
        user_id=current_user.id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=raw_key[:10],
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
    """List all active API keys for current user"""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .where(ApiKey.is_active == True)
        .order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke an API key.

    **Returns:** 204 No Content on success.

    **Errors:**
    - 401: Unauthorized
    - 403: Access denied (not your key)
    - 404: API key not found
    """
    api_key = await db.get(ApiKey, key_id)

    if not api_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")

    if api_key.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    api_key.is_active = False
    await db.commit()

    return None


# ==========================================
# Account Deletion
# ==========================================

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete user account (soft delete).

    This will:
    - Deactivate all identities
    - Revoke all API keys
    - Mark the account as deleted

    The user can re-register with the same email later.

    **Returns:** 204 No Content on success.

    **Errors:**
    - 400: Cannot delete account with active subscriptions or pending payouts
    - 401: Unauthorized
    """
    from app.models.identity import Identity
    from app.models.marketplace import Subscription

    # Check for active subscriptions
    active_sub = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        )
    )
    if active_sub.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete account with active subscription. Please cancel your subscription first."
        )

    # Soft delete all identities
    identities_result = await db.execute(
        select(Identity).where(
            Identity.user_id == current_user.id,
            Identity.deleted_at.is_(None)
        )
    )
    for identity in identities_result.scalars().all():
        identity.deleted_at = utc_now()
        identity.status = "SUSPENDED"

    # Revoke all API keys
    api_keys_result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id,
            ApiKey.is_active == True
        )
    )
    for api_key in api_keys_result.scalars().all():
        api_key.is_active = False

    # Soft delete the user
    current_user.deleted_at = utc_now()
    current_user.is_active = False

    await db.commit()

    return None


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
        # SECURITY FIX: Log error details but don't expose to client
        logger.error(f"Stripe Connect setup error: {e}", exc_info=True)
        raise HTTPException(400, "Failed to set up payout account. Please try again.")


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
        # SECURITY FIX: Log error details but don't expose to client
        logger.error(f"Stripe Connect status error: {e}", exc_info=True)
        raise HTTPException(400, "Failed to retrieve account status. Please try again.")


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
        # SECURITY FIX: Log error details but don't expose to client
        logger.error(f"Stripe dashboard link error: {e}", exc_info=True)
        raise HTTPException(400, "Failed to create dashboard link. Please try again.")


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


# ==========================================
# Creator Earnings & Payouts
# ==========================================

@router.get("/earnings")
async def get_creator_earnings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get creator's earnings summary and history.

    Returns:
        - pending_balance: Earnings still in holding period
        - available_balance: Ready for withdrawal
        - total_earned: All-time earnings
        - total_paid: Amount already paid out
        - recent_earnings: Last 20 earning records
        - next_available: When next earnings become available
    """
    from sqlalchemy import select, func
    from datetime import datetime
    from app.models.notifications import CreatorEarning, EarningStatus

    # Get balance by status
    balance_query = select(
        CreatorEarning.status,
        func.sum(CreatorEarning.net_amount).label("total")
    ).where(
        CreatorEarning.creator_id == current_user.id
    ).group_by(CreatorEarning.status)

    result = await db.execute(balance_query)
    balances = {row.status: row.total or 0 for row in result.all()}

    pending_balance = balances.get(EarningStatus.PENDING, 0)
    available_balance = balances.get(EarningStatus.AVAILABLE, 0)
    paid_balance = balances.get(EarningStatus.PAID, 0)
    refunded_balance = balances.get(EarningStatus.REFUNDED, 0)

    # Get recent earnings
    recent_query = select(CreatorEarning).where(
        CreatorEarning.creator_id == current_user.id
    ).order_by(CreatorEarning.earned_at.desc()).limit(20)

    result = await db.execute(recent_query)
    recent_earnings = result.scalars().all()

    # Get next available date
    next_available_query = select(
        func.min(CreatorEarning.available_at)
    ).where(
        CreatorEarning.creator_id == current_user.id,
        CreatorEarning.status == EarningStatus.PENDING,
        CreatorEarning.available_at > utc_now()
    )
    result = await db.execute(next_available_query)
    next_available = result.scalar_one_or_none()

    # Count earnings that should be updated to AVAILABLE
    now = utc_now()
    pending_to_available = await db.execute(
        select(func.count()).where(
            CreatorEarning.creator_id == current_user.id,
            CreatorEarning.status == EarningStatus.PENDING,
            CreatorEarning.available_at <= now
        )
    )
    matured_count = pending_to_available.scalar_one()

    # Update matured earnings to AVAILABLE
    if matured_count > 0:
        from sqlalchemy import update as sql_update
        await db.execute(
            sql_update(CreatorEarning)
            .where(
                CreatorEarning.creator_id == current_user.id,
                CreatorEarning.status == EarningStatus.PENDING,
                CreatorEarning.available_at <= now
            )
            .values(status=EarningStatus.AVAILABLE)
        )
        await db.commit()

        # Recalculate balances
        result = await db.execute(balance_query)
        balances = {row.status: row.total or 0 for row in result.all()}
        pending_balance = balances.get(EarningStatus.PENDING, 0)
        available_balance = balances.get(EarningStatus.AVAILABLE, 0)

    return {
        "pending_balance": round(pending_balance, 2),
        "available_balance": round(available_balance, 2),
        "total_earned": round(pending_balance + available_balance + paid_balance, 2),
        "total_paid": round(paid_balance, 2),
        "total_refunded": round(refunded_balance, 2),
        "currency": "USD",
        "minimum_payout": settings.PAYOUT_MINIMUM_USD,
        "holding_days": settings.PAYOUT_HOLDING_DAYS,
        "next_available": next_available.isoformat() if next_available else None,
        "can_request_payout": available_balance >= settings.PAYOUT_MINIMUM_USD,
        "recent_earnings": [
            {
                "id": str(e.id),
                "net_amount": e.net_amount,
                "gross_amount": e.gross_amount,
                "platform_fee": e.platform_fee,
                "status": e.status.value,
                "description": e.description,
                "earned_at": e.earned_at.isoformat(),
                "available_at": e.available_at.isoformat() if e.available_at else None,
                "paid_at": e.paid_at.isoformat() if e.paid_at else None,
            }
            for e in recent_earnings
        ],
    }


@router.post("/request-payout")
async def request_payout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Request a payout of available earnings.

    Requirements:
    - Available balance must be >= minimum payout ($50)
    - User must have Stripe Connect account set up
    - No pending payout request already in progress
    """
    from sqlalchemy import select, func
    from datetime import datetime
    from app.models.notifications import (
        CreatorEarning, EarningStatus,
        Payout, PayoutStatus, PayoutMethod
    )

    # Check if user has Stripe Connect
    if not current_user.stripe_connect_account_id:
        raise HTTPException(
            status_code=400,
            detail="Please set up your payout account first. Go to Settings > Payouts to connect your Stripe account."
        )

    # Verify Connect account is complete
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        account = stripe.Account.retrieve(current_user.stripe_connect_account_id)
        if not account.details_submitted:
            raise HTTPException(
                status_code=400,
                detail="Please complete your Stripe Connect onboarding before requesting a payout."
            )
        if not account.payouts_enabled:
            raise HTTPException(
                status_code=400,
                detail="Your Stripe account is pending verification. Please wait for approval."
            )
    except stripe.error.StripeError as e:
        # SECURITY: Don't expose Stripe error details in production
        logger.error("Stripe account verification failed", error=str(e), user_id=str(current_user.id))
        error_detail = f"Error verifying payout account: {str(e)}" if settings.DEBUG else "Error verifying payout account. Please try again or contact support."
        raise HTTPException(status_code=400, detail=error_detail)

    # Check for existing pending payout
    existing_payout = await db.execute(
        select(Payout).where(
            Payout.user_id == current_user.id,
            Payout.status == PayoutStatus.PENDING
        )
    )
    if existing_payout.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You already have a pending payout request. Please wait for it to be processed."
        )

    # Update matured earnings to AVAILABLE
    now = utc_now()
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(CreatorEarning)
        .where(
            CreatorEarning.creator_id == current_user.id,
            CreatorEarning.status == EarningStatus.PENDING,
            CreatorEarning.available_at <= now
        )
        .values(status=EarningStatus.AVAILABLE)
    )

    # Get available earnings
    available_earnings = await db.execute(
        select(CreatorEarning).where(
            CreatorEarning.creator_id == current_user.id,
            CreatorEarning.status == EarningStatus.AVAILABLE
        )
    )
    earnings = available_earnings.scalars().all()

    if not earnings:
        raise HTTPException(
            status_code=400,
            detail="No available earnings to withdraw. Earnings have a 7-day holding period."
        )

    # Calculate total
    total_amount = sum(e.net_amount for e in earnings)

    if total_amount < settings.PAYOUT_MINIMUM_USD:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum payout is ${settings.PAYOUT_MINIMUM_USD:.2f}. Your available balance is ${total_amount:.2f}."
        )

    # Create payout request
    payout = Payout(
        user_id=current_user.id,
        amount=total_amount,
        currency="USD",
        fee=0,  # Platform doesn't charge payout fees
        net_amount=total_amount,
        method=PayoutMethod.STRIPE_CONNECT,
        status=PayoutStatus.PENDING,
        transaction_ids=[str(e.id) for e in earnings],
        transaction_count=len(earnings),
        period_start=min(e.earned_at for e in earnings),
        period_end=max(e.earned_at for e in earnings),
        requested_at=now,
    )
    db.add(payout)
    await db.flush()

    # Mark earnings as being paid (link to payout)
    earning_ids = [e.id for e in earnings]
    await db.execute(
        sql_update(CreatorEarning)
        .where(CreatorEarning.id.in_(earning_ids))
        .values(payout_id=payout.id)
    )

    await db.commit()

    # Log the payout request
    import structlog
    logger = structlog.get_logger()
    logger.info(
        "Payout requested",
        user_id=str(current_user.id),
        payout_id=str(payout.id),
        amount=total_amount,
        earning_count=len(earnings),
    )

    return {
        "status": "success",
        "message": f"Payout request submitted for ${total_amount:.2f}",
        "payout": {
            "id": str(payout.id),
            "amount": total_amount,
            "currency": "USD",
            "status": payout.status.value,
            "earning_count": len(earnings),
            "requested_at": payout.requested_at.isoformat(),
        }
    }
