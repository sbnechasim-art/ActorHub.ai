"""
Seed Script: Generate 50 profiles per category (300 total)
Run: python scripts/seed_profiles.py
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
import sys
import json

import asyncpg

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/actorhub"

# Profile data generators
FIRST_NAMES_MALE = [
    "James", "Michael", "David", "Daniel", "Christopher", "Matthew", "Andrew", "Joshua",
    "Ryan", "Brandon", "Kevin", "Justin", "Tyler", "Jacob", "Nicholas", "William",
    "Jonathan", "Alexander", "Benjamin", "Nathan", "Samuel", "Robert", "Anthony", "Joseph",
    "Steven", "Eric", "Mark", "Brian", "Thomas", "Jason", "Jeffrey", "Richard",
    "Marcus", "Derek", "Sean", "Kyle", "Aaron", "Patrick", "Carlos", "Luis",
    "Diego", "Rafael", "Hiroshi", "Kenji", "Wei", "Jin", "Raj", "Arjun", "Omar", "Ahmed"
]

FIRST_NAMES_FEMALE = [
    "Sarah", "Emily", "Jessica", "Ashley", "Samantha", "Amanda", "Jennifer", "Elizabeth",
    "Lauren", "Megan", "Rachel", "Nicole", "Stephanie", "Hannah", "Alexis", "Victoria",
    "Kayla", "Brittany", "Danielle", "Michelle", "Natalie", "Christina", "Katherine", "Sophia",
    "Olivia", "Emma", "Isabella", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn",
    "Maria", "Carmen", "Sofia", "Valentina", "Yuki", "Sakura", "Mei", "Lin",
    "Priya", "Ananya", "Fatima", "Layla", "Nadia", "Zara", "Aisha", "Lily", "Grace", "Chloe"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin",
    "Lee", "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Green", "Baker", "Adams",
    "Nelson", "Hill", "Campbell", "Mitchell", "Roberts", "Carter", "Phillips", "Evans",
    "Turner", "Torres", "Parker", "Collins", "Edwards", "Stewart", "Morris", "Murphy",
    "Rivera", "Cook", "Rogers", "Morgan", "Peterson", "Cooper", "Reed", "Bailey",
    "Kim", "Chen", "Wang", "Yamamoto", "Tanaka", "Singh", "Patel", "Khan"
]

# High-quality Unsplash image URLs
MALE_IMAGES = [
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1463453091185-61582044d556?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1548372290-8d01b6c8e78c?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1583195764036-6dc248ac07d9?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1480455624313-e29b44bbfde1?w=400&h=400&fit=crop&crop=face",
]

FEMALE_IMAGES = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1489424731084-a5d8b219a5bb?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1499887142886-791eca5918cd?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1557862921-37829c790f19?w=400&h=400&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=400&h=400&fit=crop&crop=face",
]

# Category-specific data
CATEGORY_DATA = {
    "actor": {
        "tags_pool": ["film", "television", "theater", "commercial", "drama", "comedy", "action", "indie", "hollywood", "method acting", "voice acting", "stage", "motion capture", "period piece", "thriller"],
        "description_templates": [
            "{name} is a seasoned {adj} actor with {years} years of experience in film and television. Known for {specialty}, they bring depth and authenticity to every role.",
            "Award-nominated {adj} performer {name} specializes in {specialty}. With professional training, they deliver captivating performances across all mediums.",
            "From Broadway to Hollywood, {name} has built an impressive career spanning {years} years. Their {adj} approach to character development has earned critical acclaim.",
        ],
        "specialties": ["dramatic roles", "comedy timing", "action sequences", "emotional depth", "character transformation", "improvisation", "ensemble work", "lead performances"],
        "adjectives": ["versatile", "accomplished", "dynamic", "talented", "skilled", "dedicated", "professional", "experienced"],
        "price_range": (199, 1499),
    },
    "model": {
        "tags_pool": ["fashion", "commercial", "editorial", "runway", "fitness", "glamour", "catalog", "e-commerce", "beauty", "lifestyle", "swimwear", "athletic", "luxury", "streetwear", "haute couture"],
        "description_templates": [
            "{name} is a {adj} model with experience in {specialty}. Their striking features and professional demeanor make them perfect for high-end campaigns.",
            "International {adj} model {name} has worked with top brands in {specialty}. Their versatility spans runway, print, and digital media.",
            "With {years} years in the industry, {name} brings {adj} energy to every shoot. Specializing in {specialty}, they consistently deliver stunning results.",
        ],
        "specialties": ["high fashion editorials", "commercial campaigns", "runway shows", "beauty photography", "fitness campaigns", "lifestyle brands", "luxury advertising", "catalog work"],
        "adjectives": ["striking", "photogenic", "professional", "versatile", "elegant", "dynamic", "captivating", "refined"],
        "price_range": (149, 999),
    },
    "influencer": {
        "tags_pool": ["social media", "youtube", "tiktok", "instagram", "lifestyle", "tech", "gaming", "beauty", "fashion", "travel", "food", "fitness", "entertainment", "vlog", "brand ambassador"],
        "description_templates": [
            "{name} is a {adj} content creator with {followers}+ followers across platforms. Their engaging personality and {specialty} content resonates with millions.",
            "Digital native {name} has built a {adj} community around {specialty}. Their authentic voice and creative content drive exceptional engagement.",
            "From viral videos to brand partnerships, {name} brings {adj} energy to the digital space. Their {specialty} content has garnered {followers}+ dedicated followers.",
        ],
        "specialties": ["lifestyle content", "tech reviews", "beauty tutorials", "travel vlogs", "gaming streams", "comedy sketches", "fashion hauls", "fitness motivation"],
        "followers": ["500K", "1M", "2M", "5M", "10M", "100K", "750K", "3M"],
        "adjectives": ["engaging", "authentic", "viral", "creative", "dynamic", "influential", "trendsetting", "charismatic"],
        "price_range": (99, 799),
    },
    "character": {
        "tags_pool": ["animation", "gaming", "virtual", "avatar", "mascot", "fantasy", "sci-fi", "cartoon", "3D", "metaverse", "NFT", "digital twin", "virtual idol", "AI companion", "brand character"],
        "description_templates": [
            "{name} is a {adj} digital character designed for {specialty}. This fully-realized avatar brings {trait} to any virtual environment.",
            "Meet {name}, a {adj} character perfect for {specialty}. With expressive animations and {trait}, they captivate audiences across platforms.",
            "Created for the digital age, {name} embodies {trait} in a {adj} character package. Ideal for {specialty} and interactive experiences.",
        ],
        "specialties": ["gaming applications", "virtual events", "metaverse experiences", "animated content", "brand mascot roles", "educational content", "entertainment apps", "social VR"],
        "traits": ["endless charm", "dynamic personality", "memorable appeal", "versatile expression", "engaging presence", "unique character", "captivating design", "expressive range"],
        "adjectives": ["unique", "captivating", "versatile", "expressive", "dynamic", "memorable", "engaging", "innovative"],
        "price_range": (79, 599),
    },
    "presenter": {
        "tags_pool": ["hosting", "news", "corporate", "events", "webinar", "podcast", "broadcast", "live", "keynote", "moderator", "MC", "announcer", "spokesperson", "tutorial", "educational"],
        "description_templates": [
            "{name} is a {adj} presenter with extensive experience in {specialty}. Their clear delivery and {trait} make complex topics accessible.",
            "Seasoned {adj} host {name} brings {years} years of {specialty} experience. Their natural presence commands attention while remaining approachable.",
            "From corporate events to broadcast media, {name} delivers {adj} presentations. Their expertise in {specialty} ensures professional results every time.",
        ],
        "specialties": ["corporate events", "news broadcasting", "educational content", "product launches", "webinars", "live events", "documentary narration", "podcast hosting"],
        "traits": ["commanding presence", "natural warmth", "professional polish", "audience connection", "clear articulation", "engaging delivery", "trustworthy demeanor", "dynamic energy"],
        "adjectives": ["polished", "professional", "engaging", "articulate", "charismatic", "authoritative", "approachable", "seasoned"],
        "price_range": (149, 899),
    },
    "voice": {
        "tags_pool": ["narration", "audiobook", "commercial", "animation", "documentary", "e-learning", "IVR", "podcast", "gaming", "dubbing", "promo", "trailer", "meditation", "character voice", "corporate"],
        "description_templates": [
            "{name} is a {adj} voice artist specializing in {specialty}. Their {voice_quality} voice brings scripts to life with exceptional clarity and emotion.",
            "With a {voice_quality} tone and {adj} delivery, {name} excels in {specialty}. {years} years of experience ensure professional results.",
            "Award-winning voice talent {name} offers a {voice_quality} voice perfect for {specialty}. Their {adj} range spans commercials to character work.",
        ],
        "specialties": ["audiobook narration", "commercial voice-overs", "animation dubbing", "documentary narration", "e-learning modules", "podcast production", "gaming characters", "corporate videos"],
        "voice_qualities": ["rich baritone", "warm soprano", "versatile mid-range", "deep resonant", "bright energetic", "smooth soothing", "distinctive character", "natural conversational"],
        "adjectives": ["versatile", "expressive", "professional", "dynamic", "talented", "seasoned", "skilled", "acclaimed"],
        "price_range": (99, 699),
    },
}

# Pricing tier templates
PRICING_TEMPLATES = {
    "basic": ["10 AI generations", "Personal use only", "Standard quality", "30-day license", "Email support"],
    "pro": ["100 AI generations", "Commercial use", "HD quality", "Voice included", "90-day license", "Priority support"],
    "enterprise": ["Unlimited generations", "Full commercial rights", "4K quality", "Voice + Motion", "1-year license", "Dedicated support", "Custom training"],
}


def generate_profile(category: str, index: int) -> dict:
    """Generate a single profile for a category"""

    is_male = random.choice([True, False])
    first_name = random.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
    last_name = random.choice(LAST_NAMES)
    full_name = f"{first_name} {last_name}"

    cat_data = CATEGORY_DATA[category]

    # Select random data
    years = random.randint(3, 20)
    adj = random.choice(cat_data["adjectives"])
    specialty = random.choice(cat_data.get("specialties", ["general content"]))

    # Build description
    template = random.choice(cat_data["description_templates"])
    description = template.format(
        name=full_name,
        adj=adj,
        years=years,
        specialty=specialty,
        followers=random.choice(cat_data.get("followers", ["500K"])),
        trait=random.choice(cat_data.get("traits", cat_data.get("voice_qualities", ["exceptional skill"]))),
        voice_quality=random.choice(cat_data.get("voice_qualities", ["professional"])),
    )

    # Generate tags
    num_tags = random.randint(4, 7)
    tags = random.sample(cat_data["tags_pool"], min(num_tags, len(cat_data["tags_pool"])))
    tags.append("male" if is_male else "female")
    tags.append("professional")

    # Generate pricing
    base_price = random.randint(cat_data["price_range"][0], cat_data["price_range"][1])
    pricing_tiers = [
        {"name": "Basic", "price": base_price, "features": PRICING_TEMPLATES["basic"]},
        {"name": "Pro", "price": int(base_price * 2.5), "features": PRICING_TEMPLATES["pro"]},
        {"name": "Enterprise", "price": int(base_price * 5), "features": PRICING_TEMPLATES["enterprise"]},
    ]

    # Generate stats
    view_count = random.randint(100, 50000)
    license_count = random.randint(0, max(1, int(view_count * 0.05)))
    rating_count = random.randint(0, max(1, int(license_count * 0.8)))
    avg_rating = round(random.uniform(4.0, 5.0), 1) if rating_count > 0 else None

    # Select image
    images = MALE_IMAGES if is_male else FEMALE_IMAGES
    thumbnail_url = random.choice(images)

    # Generate slug
    slug = f"{first_name.lower()}-{last_name.lower()}-{category}-{index}"

    # Short description
    short_desc = f"{adj.capitalize()} {category} specializing in {specialty}. {years} years of experience."

    return {
        "display_name": full_name,
        "bio": description,
        "profile_image_url": thumbnail_url,
        "category": category,
        "title": f"{full_name} - {category.capitalize()} Pack",
        "slug": slug,
        "description": description,
        "short_description": short_desc[:500],
        "thumbnail_url": thumbnail_url,
        "tags": tags,
        "pricing_tiers": pricing_tiers,
        "is_featured": random.random() < 0.1,  # 10% featured
        "view_count": view_count,
        "license_count": license_count,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
    }


async def seed_database():
    """Main function to seed the database"""

    print("=" * 60)
    print("  ActorHub.ai - Seeding Database with 300 Profiles")
    print("=" * 60)

    conn = await asyncpg.connect(DATABASE_URL)

    categories = ["actor", "model", "influencer", "character", "presenter", "voice"]
    profiles_per_category = 50

    try:
        # Create a system user for seeded content
        system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        # Check if system user exists
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE id = $1",
            system_user_id
        )

        if not existing:
            await conn.execute("""
                INSERT INTO users (id, email, hashed_password, first_name, last_name, is_active, tier, created_at)
                VALUES ($1, $2, $3, $4, $5, true, 'enterprise', NOW())
            """, system_user_id, "system@actorhub.ai", "not_a_real_password_hash", "System", "Account")
            print("\n  [OK] Created system user")

        total_created = 0

        for category in categories:
            print(f"\n  Seeding {category.upper()} profiles...")
            category_created = 0

            for i in range(profiles_per_category):
                profile = generate_profile(category, i + 1)

                # Create identity
                identity_id = uuid.uuid4()
                created_at = datetime.utcnow() - timedelta(days=random.randint(1, 365))

                try:
                    await conn.execute("""
                        INSERT INTO identities (
                            id, user_id, display_name, bio, profile_image_url,
                            status, protection_level, allow_commercial_use, allow_ai_training,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, 'verified', 'pro', true, true, $6, $6)
                    """,
                        identity_id,
                        system_user_id,
                        profile["display_name"],
                        profile["bio"],
                        profile["profile_image_url"],
                        created_at
                    )

                    # Create listing
                    listing_id = uuid.uuid4()

                    await conn.execute("""
                        INSERT INTO listings (
                            id, identity_id, title, slug, description, short_description,
                            thumbnail_url, category, tags, pricing_tiers,
                            is_active, is_featured, view_count, license_count,
                            avg_rating, rating_count, created_at, updated_at, published_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true, $11, $12, $13, $14, $15, $16, $16, $16)
                    """,
                        listing_id,
                        identity_id,
                        profile["title"],
                        profile["slug"],
                        profile["description"],
                        profile["short_description"],
                        profile["thumbnail_url"],
                        category,
                        profile["tags"],
                        json.dumps(profile["pricing_tiers"]),
                        profile["is_featured"],
                        profile["view_count"],
                        profile["license_count"],
                        profile["avg_rating"],
                        profile["rating_count"],
                        created_at
                    )

                    category_created += 1
                    total_created += 1

                except asyncpg.UniqueViolationError:
                    # Skip duplicates
                    pass

                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"      Created {i + 1}/{profiles_per_category} {category} profiles")

            print(f"    [OK] Created {category_created} {category} profiles")

        print("\n" + "=" * 60)
        print(f"  SUCCESS: Created {total_created} profiles total!")
        print("=" * 60)

        # Verify counts
        print("\n  Final counts:")
        for category in categories:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM listings WHERE category = $1",
                category
            )
            print(f"    {category.capitalize()}: {count} listings")

        total = await conn.fetchval("SELECT COUNT(*) FROM listings")
        print(f"\n    TOTAL: {total} listings in database")

        return True

    except Exception as e:
        print(f"\n  [ERROR] Failed to seed database: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(seed_database())
    sys.exit(0 if success else 1)
