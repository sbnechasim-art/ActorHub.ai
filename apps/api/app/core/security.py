"""
Security utilities
JWT handling, password hashing, API key validation

SECURITY UPDATE 2024-12-21:
- Migrated from python-jose to PyJWT due to CVE-2024-33663, CVE-2024-33664
- python-jose had JWT signature bypass vulnerabilities
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.monitoring import AUTH_FAILURES, AUTH_SUCCESS, API_KEY_VALIDATIONS

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token (short-lived: 15 minutes default)"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now, "type": "access"})

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token (long-lived: 7 days default)"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})

    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT refresh token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_REFRESH_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "type"]}
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except PyJWTError:
        return None


def decode_token(token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token.

    SECURITY FIX: Now validates token type AND uses correct secret per token type.
    - Access tokens use JWT_SECRET
    - Refresh tokens use JWT_REFRESH_SECRET
    This prevents token confusion attacks where a refresh token is used as access token.
    """
    try:
        # CRITICAL FIX: Use correct secret based on expected token type
        secret = settings.JWT_REFRESH_SECRET if expected_type == "refresh" else settings.JWT_SECRET

        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "type"]}
        )
        # SECURITY: Validate token type to prevent token confusion
        if payload.get("type") != expected_type:
            return None
        return payload
    except PyJWTError:
        return None


def create_2fa_pending_token(user_id: str) -> str:
    """
    Create a short-lived token for 2FA verification.

    SECURITY: This token proves the user passed the first factor (password)
    and is only valid for completing 2FA within 5 minutes.
    This prevents the account takeover vulnerability where user_id was
    accepted directly without proof of password authentication.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=5)  # Very short-lived

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "2fa_pending",
    }

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_2fa_pending_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a 2FA pending token.

    SECURITY: Only accepts tokens with type "2fa_pending" to ensure
    the user has already passed password authentication.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "type"]}
        )
        if payload.get("type") != "2fa_pending":
            return None
        return payload
    except PyJWTError:
        return None


def generate_api_key() -> str:
    """Generate a new API key"""
    return f"ah_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage using bcrypt.

    SECURITY FIX: Changed from SHA256 to bcrypt.
    SHA256 is fast and vulnerable to rainbow tables/GPU cracking.
    bcrypt is designed for password/secret hashing with built-in salt.

    Note: This requires updating the api_keys.key_hash column from VARCHAR(64)
    to VARCHAR(72) to accommodate bcrypt hashes.
    """
    return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its bcrypt hash.

    SECURITY: bcrypt uses constant-time comparison internally.
    """
    try:
        return bcrypt.checkpw(api_key.encode('utf-8'), hashed_key.encode('utf-8'))
    except Exception:
        return False


def hash_api_key_sha256(api_key: str) -> str:
    """
    Legacy SHA256 hash for API keys.

    DEPRECATED: Only used for migration from old keys.
    New keys should use hash_api_key() with bcrypt.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """
    Extract JWT token from request.
    Priority: Authorization header > httpOnly cookie
    """
    # First try Authorization header
    if credentials and credentials.credentials:
        return credentials.credentials

    # Fall back to httpOnly cookie
    cookie_token = request.cookies.get(settings.COOKIE_ACCESS_TOKEN_NAME)
    if cookie_token:
        return cookie_token

    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user from JWT token.

    Token can be provided via:
    1. Authorization header (Bearer token) - for API clients
    2. httpOnly cookie (access_token) - for browser clients
    """
    token = _extract_token(request, credentials)

    if not token:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="jwt", reason="missing").inc()
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if not payload:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="jwt", reason="invalid").inc()
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="jwt", reason="invalid_payload").inc()
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Get user from database
    from sqlalchemy import select

    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="jwt", reason="user_not_found").inc()
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="jwt", reason="user_inactive").inc()
        raise HTTPException(status_code=401, detail="User is inactive")

    # SECURITY: Check if token was issued before password change (session invalidation)
    if user.password_changed_at:
        token_iat = payload.get("iat")
        if token_iat:
            # Convert iat timestamp to datetime
            if isinstance(token_iat, (int, float)):
                token_issued_at = datetime.fromtimestamp(token_iat, tz=timezone.utc)
            else:
                token_issued_at = token_iat

            # Make password_changed_at timezone-aware if needed
            pwd_changed = user.password_changed_at
            if pwd_changed.tzinfo is None:
                pwd_changed = pwd_changed.replace(tzinfo=timezone.utc)

            # If token was issued before password change, invalidate it
            if token_issued_at < pwd_changed:
                AUTH_FAILURES.labels(type="jwt", reason="password_changed").inc()
                raise HTTPException(
                    status_code=401,
                    detail="Session expired due to password change. Please log in again."
                )

    # HIGH FIX: Track successful auth
    AUTH_SUCCESS.labels(type="jwt").inc()
    return user


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header), db: AsyncSession = Depends(get_db)
):
    """
    Validate API key and return associated key record.

    SECURITY FIX: Now uses bcrypt verification with fallback to legacy SHA256.
    PERF FIX: Added Redis caching to avoid repeated bcrypt comparisons.
    """
    if not api_key:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="api_key", reason="missing").inc()
        raise HTTPException(status_code=401, detail="API key required")

    from sqlalchemy import select

    from app.models.user import ApiKey
    from app.services.cache import redis_client

    # Check Redis cache first (key_id stored by api_key hash)
    cache_key = f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    cached_key_id = None

    try:
        if redis_client:
            cached_key_id = await redis_client.get(cache_key)
    except Exception:
        pass  # Redis unavailable, continue without cache

    key_record = None

    if cached_key_id:
        # Fast path: fetch by cached ID
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.id == cached_key_id,
                ApiKey.is_active.is_(True)
            )
        )
        key_record = result.scalar_one_or_none()

        # Verify the key still matches (in case of collision or key rotation)
        if key_record and not verify_api_key(api_key, key_record.key_hash):
            key_record = None
            # Invalidate stale cache
            try:
                if redis_client:
                    await redis_client.delete(cache_key)
            except Exception:
                pass

    if not key_record:
        # Slow path: lookup by prefix and verify with bcrypt
        key_prefix = api_key[:10] if len(api_key) >= 10 else api_key

        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_prefix == key_prefix,
                ApiKey.is_active.is_(True)
            )
        )
        key_records = result.scalars().all()

        # Verify against bcrypt hash
        for record in key_records:
            if verify_api_key(api_key, record.key_hash):
                key_record = record
                break

        # Fallback: Try legacy SHA256 lookup for old keys (migration support)
        if not key_record:
            legacy_hash = hash_api_key_sha256(api_key)
            result = await db.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == legacy_hash,
                    ApiKey.is_active.is_(True)
                )
            )
            key_record = result.scalar_one_or_none()

            # If found with legacy hash, upgrade to bcrypt
            if key_record:
                key_record.key_hash = hash_api_key(api_key)
                key_record.key_prefix = api_key[:10] if len(api_key) >= 10 else api_key

        # Cache the verified key ID for future requests (1 hour TTL)
        # HIGH FIX: Use SET with NX to prevent race condition overwrites
        if key_record:
            try:
                if redis_client:
                    # Use nx=True (SET if Not eXists) to prevent race conditions
                    # If another request already cached this key, we don't overwrite
                    await redis_client.set(cache_key, str(key_record.id), ex=3600, nx=True)
            except Exception:
                pass

    if not key_record:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="api_key", reason="invalid").inc()
        API_KEY_VALIDATIONS.labels(status="invalid").inc()
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check expiration
    # CRITICAL FIX: Use timezone-aware datetime to prevent comparison bugs
    now = datetime.now(timezone.utc)
    if key_record.expires_at and key_record.expires_at < now:
        # HIGH FIX: Track auth failures
        AUTH_FAILURES.labels(type="api_key", reason="expired").inc()
        API_KEY_VALIDATIONS.labels(status="expired").inc()
        raise HTTPException(status_code=401, detail="API key expired")

    # HIGH FIX: Track successful API key auth
    AUTH_SUCCESS.labels(type="api_key").inc()
    API_KEY_VALIDATIONS.labels(status="valid").inc()

    # Update last used (async, don't block the response)
    key_record.last_used_at = now
    key_record.usage_count += 1
    await db.commit()

    return key_record


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Get current user if authenticated, None otherwise"""
    token = _extract_token(request, credentials)
    if not token:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


# ===========================================
# Role-Based Access Control Dependencies
# ===========================================

# SECURITY FIX: Granular admin permissions
# Different admin operations require different permission levels
class AdminPermission:
    """Admin permission constants for granular access control."""
    # Read-only access
    READ_DASHBOARD = "admin.dashboard.read"
    READ_USERS = "admin.users.read"
    READ_ANALYTICS = "admin.analytics.read"
    READ_PAYOUTS = "admin.payouts.read"
    READ_REFUNDS = "admin.refunds.read"

    # Write access (sensitive operations)
    MANAGE_USERS = "admin.users.write"      # Ban/unban, verify users
    MANAGE_IDENTITIES = "admin.identities.write"  # Approve/reject identities
    PROCESS_PAYOUTS = "admin.payouts.write"  # Financial: process payouts
    PROCESS_REFUNDS = "admin.refunds.write"  # Financial: process refunds
    MANAGE_LISTINGS = "admin.listings.write"  # Feature/unfeature listings

    # Super admin only
    MANAGE_ADMINS = "admin.admins.write"    # Create/remove admin access


# Define permission levels for different admin roles
ADMIN_ROLE_PERMISSIONS = {
    "ADMIN": [
        # Full access
        AdminPermission.READ_DASHBOARD,
        AdminPermission.READ_USERS,
        AdminPermission.READ_ANALYTICS,
        AdminPermission.READ_PAYOUTS,
        AdminPermission.READ_REFUNDS,
        AdminPermission.MANAGE_USERS,
        AdminPermission.MANAGE_IDENTITIES,
        AdminPermission.PROCESS_PAYOUTS,
        AdminPermission.PROCESS_REFUNDS,
        AdminPermission.MANAGE_LISTINGS,
        AdminPermission.MANAGE_ADMINS,
    ],
    "MODERATOR": [
        # Read access + content moderation
        AdminPermission.READ_DASHBOARD,
        AdminPermission.READ_USERS,
        AdminPermission.MANAGE_USERS,  # Can ban users
        AdminPermission.MANAGE_IDENTITIES,
        AdminPermission.MANAGE_LISTINGS,
    ],
    "SUPPORT": [
        # Read access + refund processing
        AdminPermission.READ_DASHBOARD,
        AdminPermission.READ_USERS,
        AdminPermission.READ_REFUNDS,
        AdminPermission.PROCESS_REFUNDS,
    ],
    "ANALYST": [
        # Read-only analytics access
        AdminPermission.READ_DASHBOARD,
        AdminPermission.READ_ANALYTICS,
    ],
}


def has_permission(user, permission: str) -> bool:
    """Check if user has a specific admin permission."""
    if not user.role:
        return False

    user_permissions = ADMIN_ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_permissions


def require_permission(permission: str):
    """
    Dependency factory that requires a specific admin permission.

    Usage:
        @router.post("/payouts/{id}/process")
        async def process_payout(
            admin: User = Depends(require_permission(AdminPermission.PROCESS_PAYOUTS))
        ):
    """
    async def permission_dependency(current_user = Depends(get_current_user)):
        import structlog
        logger = structlog.get_logger()

        if not has_permission(current_user, permission):
            logger.warning(
                "Admin permission denied",
                user_id=str(current_user.id),
                role=current_user.role or "None",
                required_permission=permission,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return permission_dependency


async def require_admin(
    current_user = Depends(get_current_user),
):
    """
    Dependency that requires admin role (any admin permission level).
    Use as: admin: User = Depends(require_admin)

    For more granular control, use require_permission() instead.
    """
    from app.models.user import User
    import structlog
    logger = structlog.get_logger()

    # Allow any role that has admin permissions
    if current_user.role not in ADMIN_ROLE_PERMISSIONS:
        logger.warning(
            "Admin access denied",
            user_id=str(current_user.id),
            role=current_user.role or "None",
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user


async def require_creator(
    current_user = Depends(get_current_user),
):
    """
    Dependency that requires creator or admin role.
    Use as: creator: User = Depends(require_creator)
    """
    if current_user.role not in ("CREATOR", "ADMIN"):
        raise HTTPException(
            status_code=403,
            detail="Creator access required",
        )
    return current_user
