"""
User Service
Business logic for user operations

Encapsulates:
- User registration and authentication
- Profile management
- Dashboard statistics
- Stripe customer management
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User, ApiKey

logger = structlog.get_logger()


class UserService:
    """Service for user-related operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===========================================
    # User Registration & Authentication
    # ===========================================

    async def get_by_email(self, email: str, include_deleted: bool = False) -> Optional[User]:
        """Get user by email address (excludes soft-deleted by default)"""
        query = select(User).where(User.email == email)
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return await self.db.get(User, user_id)

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered"""
        user = await self.get_by_email(email)
        return user is not None

    async def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> User:
        """
        Create a new user.

        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            first_name: User's first name
            last_name: User's last name
            display_name: Display name (defaults to email prefix)

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists
        """
        if await self.email_exists(email):
            raise ValueError("Email already registered")

        user = User(
            email=email,
            hashed_password=hash_password(password) if password else None,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name or email.split("@")[0],
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info("User created", user_id=str(user.id), email=email)
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Returns:
            User if credentials are valid, None otherwise
        """
        user = await self.get_by_email(email)

        if not user or not user.hashed_password:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login_at = utc_now()
        await self.db.commit()

        return user

    def create_tokens(self, user: User) -> Dict[str, Any]:
        """Create access and refresh tokens for user"""
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    # ===========================================
    # Profile Management
    # ===========================================

    async def update_profile(
        self,
        user: User,
        updates: Dict[str, Any],
        allowed_fields: set,
    ) -> User:
        """
        Update user profile with validated fields.

        Args:
            user: User to update
            updates: Dictionary of field updates
            allowed_fields: Set of field names that can be updated

        Returns:
            Updated User object

        Raises:
            ValueError: If trying to update disallowed field
        """
        for field, value in updates.items():
            if field not in allowed_fields:
                raise ValueError(f"Field '{field}' cannot be modified")
            setattr(user, field, value)

        user.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(user)

        return user

    # ===========================================
    # Dashboard Statistics
    # ===========================================

    async def get_dashboard_stats(self, user: User) -> Dict[str, Any]:
        """Get dashboard statistics for a user"""
        from app.models.identity import Identity
        from app.models.marketplace import License

        # Count identities
        identities_count = await self.db.scalar(
            select(func.count(Identity.id)).where(
                Identity.user_id == user.id,
                Identity.deleted_at.is_(None),
            )
        ) or 0

        # Sum revenue
        total_revenue = await self.db.scalar(
            select(func.coalesce(func.sum(Identity.total_revenue), 0)).where(
                Identity.user_id == user.id
            )
        ) or 0

        # Sum verifications
        total_verifications = await self.db.scalar(
            select(func.coalesce(func.sum(Identity.total_verifications), 0)).where(
                Identity.user_id == user.id
            )
        ) or 0

        # Count active licenses
        try:
            licenses_count = await self.db.scalar(
                select(func.count(License.id))
                .join(Identity)
                .where(
                    Identity.user_id == user.id,
                    License.is_active.is_(True),
                )
            ) or 0
        except Exception:
            licenses_count = 0

        return {
            "identities_count": identities_count,
            "total_revenue": float(total_revenue),
            "verification_checks": int(total_verifications),
            "active_licenses": licenses_count,
            "user_tier": user.tier if isinstance(user.tier, str) else user.tier.value,
        }

    # ===========================================
    # Stripe Customer Management
    # ===========================================

    async def ensure_stripe_customer(self, user: User) -> str:
        """
        Ensure user has a Stripe customer ID, creating one if needed.

        Returns:
            Stripe customer ID
        """
        if user.stripe_customer_id:
            return user.stripe_customer_id

        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if not stripe.api_key:
            raise ValueError("Stripe not configured")

        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name or user.email,
            metadata={"user_id": str(user.id)},
        )

        user.stripe_customer_id = customer.id
        await self.db.commit()

        logger.info(
            "Stripe customer created",
            user_id=str(user.id),
            customer_id=customer.id,
        )

        return customer.id

    # ===========================================
    # API Key Management
    # ===========================================

    async def get_api_keys(self, user: User) -> List[ApiKey]:
        """Get all API keys for a user"""
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user.id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_api_key(
        self,
        user: User,
        name: str,
        permissions: List[str],
        rate_limit: int = 100,
        expires_in_days: Optional[int] = None,
    ) -> tuple[str, ApiKey]:
        """
        Create a new API key for a user.

        Returns:
            Tuple of (raw_key, ApiKey record)
        """
        from app.core.security import generate_api_key, hash_api_key

        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)

        expires_at = None
        if expires_in_days:
            expires_at = utc_now() + timedelta(days=expires_in_days)

        api_key = ApiKey(
            user_id=user.id,
            name=name,
            key_hash=key_hash,
            key_prefix=raw_key[:8],
            permissions=permissions,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(
            "API key created",
            user_id=str(user.id),
            key_name=name,
            key_prefix=raw_key[:8],
        )

        return raw_key, api_key

    async def revoke_api_key(self, user: User, key_id: UUID) -> bool:
        """
        Revoke an API key.

        Returns:
            True if key was revoked, False if not found or not owned
        """
        api_key = await self.db.get(ApiKey, key_id)

        if not api_key:
            return False

        if api_key.user_id != user.id:
            return False

        api_key.is_active = False
        await self.db.commit()

        logger.info(
            "API key revoked",
            user_id=str(user.id),
            key_id=str(key_id),
        )

        return True


# ===========================================
# Dependency for FastAPI
# ===========================================

async def get_user_service(db: AsyncSession) -> UserService:
    """FastAPI dependency for UserService"""
    return UserService(db)
