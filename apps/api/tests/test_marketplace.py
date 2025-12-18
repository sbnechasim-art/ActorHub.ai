"""
Marketplace API Tests
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import Identity, IdentityStatus, ProtectionLevel
from app.models.marketplace import Listing, ListingCategory


class TestMarketplaceListings:
    """Test marketplace listing endpoints"""

    @pytest.fixture
    async def test_identity(self, db_session: AsyncSession, test_user) -> Identity:
        """Create a test identity for marketplace tests"""
        identity = Identity(
            user_id=test_user.id,
            display_name="Test Celebrity",
            status=IdentityStatus.VERIFIED,
            protection_level=ProtectionLevel.PRO,
            allow_commercial_use=True,
            allow_ai_training=False,
            base_license_fee=99.0,
        )
        db_session.add(identity)
        await db_session.commit()
        await db_session.refresh(identity)
        return identity

    @pytest.fixture
    async def test_listing(
        self, db_session: AsyncSession, test_identity: Identity
    ) -> Listing:
        """Create a test listing"""
        listing = Listing(
            identity_id=test_identity.id,
            title="Test Celebrity Listing",
            slug="test-celebrity-listing-abc123",
            description="A test listing for marketplace tests",
            short_description="Test listing",
            category=ListingCategory.ACTOR,
            tags=["test", "actor"],
            pricing_tiers=[
                {"type": "single_use", "price": 99, "duration_days": 30}
            ],
            is_active=True,
        )
        db_session.add(listing)
        await db_session.commit()
        await db_session.refresh(listing)
        return listing

    @pytest.mark.asyncio
    async def test_search_listings_empty(self, client: AsyncClient):
        """Test searching listings when none exist"""
        response = await client.get("/api/v1/marketplace/listings")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_search_listings_with_results(
        self, client: AsyncClient, test_listing: Listing
    ):
        """Test searching listings with results"""
        response = await client.get("/api/v1/marketplace/listings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Test Celebrity Listing"

    @pytest.mark.asyncio
    async def test_search_listings_with_query(
        self, client: AsyncClient, test_listing: Listing
    ):
        """Test searching listings with search query"""
        response = await client.get(
            "/api/v1/marketplace/listings", params={"query": "Celebrity"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_search_listings_with_category(
        self, client: AsyncClient, test_listing: Listing
    ):
        """Test filtering listings by category"""
        response = await client.get(
            "/api/v1/marketplace/listings", params={"category": "actor"}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(item["category"] == "actor" for item in data)

    @pytest.mark.asyncio
    async def test_get_listing_by_id(
        self, client: AsyncClient, test_listing: Listing
    ):
        """Test getting a specific listing"""
        response = await client.get(
            f"/api/v1/marketplace/listings/{test_listing.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_listing.id)
        assert data["title"] == "Test Celebrity Listing"

    @pytest.mark.asyncio
    async def test_get_nonexistent_listing(self, client: AsyncClient):
        """Test getting a listing that doesn't exist"""
        import uuid
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/marketplace/listings/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_listing_authenticated(
        self, auth_client: AsyncClient, test_identity: Identity
    ):
        """Test creating a listing when authenticated"""
        response = await auth_client.post(
            "/api/v1/marketplace/listings",
            json={
                "identity_id": str(test_identity.id),
                "title": "New Test Listing",
                "description": "A brand new listing",
                "short_description": "New listing",
                "category": "model",
                "tags": ["new", "model"],
                "pricing_tiers": [
                    {"type": "single_use", "price": 149, "duration_days": 30}
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Test Listing"

    @pytest.mark.asyncio
    async def test_create_listing_unauthenticated(self, client: AsyncClient):
        """Test creating a listing without authentication"""
        response = await client.post(
            "/api/v1/marketplace/listings",
            json={
                "identity_id": "00000000-0000-0000-0000-000000000000",
                "title": "Unauthorized Listing",
            },
        )
        assert response.status_code == 401


class TestLicensePricing:
    """Test license pricing calculation"""

    @pytest.fixture
    async def test_identity(self, db_session: AsyncSession, test_user) -> Identity:
        """Create a test identity for pricing tests"""
        identity = Identity(
            user_id=test_user.id,
            display_name="Pricing Test Identity",
            status=IdentityStatus.VERIFIED,
            protection_level=ProtectionLevel.PRO,
            allow_commercial_use=True,
            base_license_fee=100.0,
        )
        db_session.add(identity)
        await db_session.commit()
        await db_session.refresh(identity)
        return identity

    @pytest.mark.asyncio
    async def test_calculate_price_personal(
        self, client: AsyncClient, test_identity: Identity
    ):
        """Test price calculation for personal use"""
        response = await client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "standard",
                "usage_type": "personal",
                "duration_days": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_price" in data
        assert data["total_price"] > 0

    @pytest.mark.asyncio
    async def test_calculate_price_commercial(
        self, client: AsyncClient, test_identity: Identity
    ):
        """Test price calculation for commercial use"""
        response = await client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(test_identity.id),
                "license_type": "standard",
                "usage_type": "commercial",
                "duration_days": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Commercial should be more expensive than personal
        assert data["usage_multiplier"] == 3.0

    @pytest.mark.asyncio
    async def test_calculate_price_nonexistent_identity(self, client: AsyncClient):
        """Test price calculation for nonexistent identity"""
        import uuid
        response = await client.post(
            "/api/v1/marketplace/license/price",
            json={
                "identity_id": str(uuid.uuid4()),
                "license_type": "standard",
                "usage_type": "personal",
                "duration_days": 30,
            },
        )
        assert response.status_code == 404


class TestCategories:
    """Test marketplace categories endpoint"""

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient):
        """Test getting available categories"""
        response = await client.get("/api/v1/marketplace/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
        # Verify category structure
        category = data["categories"][0]
        assert "id" in category
        assert "name" in category
        assert "description" in category
