"""
Database Seed Script
Creates initial data for testing
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker, init_db
from app.core.security import hash_password, generate_api_key, hash_api_key
from app.models.user import User, ApiKey, UserRole, UserTier
from app.models.identity import Identity, ActorPack, IdentityStatus, ProtectionLevel, TrainingStatus
from app.models.marketplace import Listing
import uuid
from datetime import datetime


async def seed_database():
    """Seed the database with test data"""
    print("Initializing database...")
    await init_db()

    async with async_session_maker() as db:
        # Create test user
        print("Creating test user...")
        test_user = User(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            email="test@actorhub.ai",
            hashed_password=hash_password("password123"),
            first_name="Test",
            last_name="User",
            display_name="TestUser",
            role=UserRole.CREATOR,
            tier=UserTier.PRO,
            is_active=True,
            email_verified=True,
        )
        db.add(test_user)

        # Create admin user
        print("Creating admin user...")
        admin_user = User(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            email="admin@actorhub.ai",
            hashed_password=hash_password("admin123"),
            first_name="Admin",
            last_name="User",
            display_name="Admin",
            role=UserRole.ADMIN,
            tier=UserTier.ENTERPRISE,
            is_active=True,
            email_verified=True,
        )
        db.add(admin_user)

        # Create API key for test user
        print("Creating API key...")
        raw_api_key = "ah_test_key_for_development_only"
        api_key = ApiKey(
            user_id=test_user.id,
            name="Development Key",
            key_hash=hash_api_key(raw_api_key),
            key_prefix=raw_api_key[:8],
            permissions=["verify", "read", "write"],
            rate_limit=1000,
            is_active=True,
        )
        db.add(api_key)

        # Create test identity
        print("Creating test identity...")
        test_identity = Identity(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            user_id=test_user.id,
            display_name="John Actor",
            bio="Professional actor and voice artist",
            status=IdentityStatus.VERIFIED,
            verified_at=datetime.utcnow(),
            verification_method="selfie",
            protection_level=ProtectionLevel.PRO,
            allow_commercial_use=True,
            allow_ai_training=False,
            blocked_categories=["adult", "political"],
            base_license_fee=99.0,
            hourly_rate=50.0,
            total_verifications=150,
            total_licenses=12,
            total_revenue=2500.0,
        )
        db.add(test_identity)

        # Create test actor pack
        print("Creating test actor pack...")
        test_actor_pack = ActorPack(
            identity_id=test_identity.id,
            name="John Actor Pack v1",
            description="High-quality face and voice model for commercial use",
            version="1.0.0",
            slug="john-actor-v1",
            training_status=TrainingStatus.COMPLETED,
            training_completed_at=datetime.utcnow(),
            training_images_count=25,
            training_audio_seconds=120,
            quality_score=92.5,
            authenticity_score=94.0,
            consistency_score=90.0,
            voice_quality_score=88.0,
            components={
                "face": True,
                "voice": True,
                "motion": False
            },
            base_price_usd=199.0,
            price_per_second_usd=0.10,
            price_per_image_usd=5.0,
            is_public=True,
            is_available=True,
            total_downloads=45,
            total_uses=230,
            total_revenue_usd=4500.0,
            avg_rating=4.8,
            rating_count=23,
        )
        db.add(test_actor_pack)

        # Create test listing
        print("Creating test listing...")
        test_listing = Listing(
            identity_id=test_identity.id,
            title="John Actor - Professional AI Model",
            slug="john-actor-professional",
            description="High-quality AI-ready model of professional actor John. Perfect for commercials, presentations, and creative projects.",
            short_description="Professional actor model with face and voice",
            category="actor",
            tags=["professional", "commercial", "voice", "male"],
            pricing_tiers=[
                {
                    "name": "Basic",
                    "price": 99,
                    "features": ["10 images", "Personal use only"]
                },
                {
                    "name": "Pro",
                    "price": 299,
                    "features": ["Unlimited images", "Voice included", "Commercial use"]
                },
                {
                    "name": "Enterprise",
                    "price": 999,
                    "features": ["Everything in Pro", "Priority support", "Custom training"]
                }
            ],
            is_active=True,
            is_featured=True,
            view_count=1250,
            favorite_count=89,
            license_count=12,
            avg_rating=4.8,
            rating_count=23,
            published_at=datetime.utcnow(),
        )
        db.add(test_listing)

        await db.commit()

        print("\n" + "="*50)
        print("Database seeded successfully!")
        print("="*50)
        print("\nTest Accounts:")
        print(f"  User: test@actorhub.ai / password123")
        print(f"  Admin: admin@actorhub.ai / admin123")
        print(f"\nAPI Key: {raw_api_key}")
        print(f"\nTest Identity ID: 33333333-3333-3333-3333-333333333333")
        print("="*50)


if __name__ == "__main__":
    asyncio.run(seed_database())
