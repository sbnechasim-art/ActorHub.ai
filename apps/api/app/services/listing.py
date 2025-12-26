"""
Listing Service

Handles automatic creation and management of marketplace listings.
"""

import uuid
from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime

from app.models.identity import Identity
from app.models.marketplace import Listing

logger = structlog.get_logger()

# Default pricing tiers for auto-created listings
DEFAULT_PRICING_TIERS = [
    {
        "name": "Basic",
        "price": 99,
        "features": [
            "10 AI generations",
            "Personal use only",
            "Standard quality",
            "30-day license",
            "Email support"
        ]
    },
    {
        "name": "Pro",
        "price": 249,
        "features": [
            "100 AI generations",
            "Commercial use",
            "HD quality",
            "Voice included",
            "90-day license",
            "Priority support"
        ]
    },
    {
        "name": "Enterprise",
        "price": 499,
        "features": [
            "Unlimited generations",
            "Full commercial rights",
            "4K quality",
            "Voice + Motion",
            "1-year license",
            "Dedicated support",
            "Custom training"
        ]
    }
]


class ListingService:
    """Service for managing marketplace listings"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_listing_for_identity(self, identity_id: uuid.UUID) -> Optional[Listing]:
        """Get the active listing for an identity, if exists"""
        stmt = select(Listing).where(
            Listing.identity_id == identity_id,
            Listing.is_active.is_(True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_basic_listing(self, identity: Identity) -> Optional[Listing]:
        """
        Create a basic marketplace listing for an identity.

        Only creates if:
        - Identity allows commercial use
        - Identity is set to show in public gallery
        - No active listing already exists

        Returns the created listing or None if conditions not met.
        """
        # Check conditions
        if not identity.allow_commercial_use:
            logger.debug("Skipping listing creation - commercial use not allowed",
                        identity_id=str(identity.id))
            return None

        if not identity.show_in_public_gallery:
            logger.debug("Skipping listing creation - not set to show in gallery",
                        identity_id=str(identity.id))
            return None

        # Check if listing already exists
        existing = await self.get_listing_for_identity(identity.id)
        if existing:
            logger.debug("Listing already exists for identity",
                        identity_id=str(identity.id),
                        listing_id=str(existing.id))
            return existing

        # Generate slug
        base_slug = identity.display_name.lower().replace(" ", "-")[:50]
        slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"

        # Create basic listing
        listing = Listing(
            identity_id=identity.id,
            title=f"{identity.display_name} - Actor Pack",
            slug=slug,
            description=self._generate_description(identity),
            short_description=f"Licensed AI-ready identity pack for {identity.display_name}.",
            thumbnail_url=identity.profile_image_url,
            preview_images=[],
            category="ACTOR",
            tags=["professional", "verified"],
            pricing_tiers=DEFAULT_PRICING_TIERS,
            is_active=True,
            is_featured=False,
            requires_approval=False,
            published_at=utc_now(),
        )

        self.db.add(listing)
        await self.db.flush()

        logger.info("Created basic marketplace listing",
                   identity_id=str(identity.id),
                   listing_id=str(listing.id),
                   title=listing.title)

        return listing

    async def update_or_create_listing(self, identity: Identity) -> Optional[Listing]:
        """
        Update existing listing or create new one based on identity settings.

        - If commercial use and gallery are enabled: create listing if not exists
        - If either is disabled: deactivate existing listing
        """
        existing = await self.get_listing_for_identity(identity.id)

        # Should have listing?
        should_have_listing = identity.allow_commercial_use and identity.show_in_public_gallery

        if should_have_listing:
            if existing:
                # Update thumbnail if changed
                if existing.thumbnail_url != identity.profile_image_url:
                    existing.thumbnail_url = identity.profile_image_url
                    existing.updated_at = utc_now()
                return existing
            else:
                # Create new listing
                return await self.create_basic_listing(identity)
        else:
            # Deactivate existing listing if conditions no longer met
            if existing:
                existing.is_active = False
                existing.updated_at = utc_now()
                logger.info("Deactivated listing - conditions no longer met",
                           identity_id=str(identity.id),
                           listing_id=str(existing.id))
            return None

    def _generate_description(self, identity: Identity) -> str:
        """Generate a default description for the listing"""
        protection_level = identity.protection_level or "FREE"

        return f"""## {identity.display_name}

A verified AI-ready identity pack available for licensing.

### What's Included
- High-quality verified identity
- AI training-ready assets
- Commercial usage rights
- Face verification data

### Protection Level
{protection_level.title()} tier protection with full verification.

### Usage Rights
This identity is available for commercial AI applications including:
- AI-generated content
- Virtual avatars
- Digital marketing
- Creative projects

All uses must comply with the license terms and respect the identity owner's preferences.
"""
