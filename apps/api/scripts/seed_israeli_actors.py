"""
Seed Israeli Actors to Marketplace
Upload actor images and create marketplace listings

Run from apps/api directory:
  python scripts/seed_israeli_actors.py
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import boto3
from botocore.config import Config

# Configuration
DB_URL = "postgresql://postgres:postgres@localhost:5433/actorhub"
S3_ENDPOINT = "http://localhost:9000"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"
S3_BUCKET = "actorhub-uploads"

# Hebrew to English name mapping for Israeli actors
ACTOR_NAMES = {
    "אלקנה בוחבוט": {"en": "Elkana Buchbut", "category": "ACTOR", "gender": "male"},
    "אנה זק": {"en": "Anna Zak", "category": "INFLUENCER", "gender": "female"},
    "בר זומר": {"en": "Bar Zomer", "category": "ACTOR", "gender": "female"},
    "בר רפאלי": {"en": "Bar Refaeli", "category": "MODEL", "gender": "female"},
    "גל גדות": {"en": "Gal Gadot", "category": "ACTOR", "gender": "female"},
    "דני קושמרו": {"en": "Danny Kushmaro", "category": "PRESENTER", "gender": "male"},
    "דניאל גד": {"en": "Daniel Gad", "category": "ACTOR", "gender": "male"},
    "דניאל עמית": {"en": "Daniel Amit", "category": "ACTOR", "gender": "male"},
    "חני וינברגר": {"en": "Hani Weinberger", "category": "ACTOR", "gender": "female"},
    "יהודה לוי": {"en": "Yehuda Levi", "category": "ACTOR", "gender": "male"},
    "יעל גולדמן": {"en": "Yael Goldman", "category": "PRESENTER", "gender": "female"},
    "יעל שלביה": {"en": "Yael Shelbia", "category": "MODEL", "gender": "female"},
    "ליאור רז": {"en": "Lior Raz", "category": "ACTOR", "gender": "male"},
    "לירן כוהנר": {"en": "Liran Kohner", "category": "ACTOR", "gender": "female"},
    "מגי טביב": {"en": "Magi Taviv", "category": "ACTOR", "gender": "female"},
    "נועה קירל": {"en": "Noa Kirel", "category": "INFLUENCER", "gender": "female"},
    "עדן פינס": {"en": "Eden Fines", "category": "ACTOR", "gender": "female"},
    "עומר אדם": {"en": "Omer Adam", "category": "VOICE", "gender": "male"},
    "עומר נודלמן": {"en": "Omer Nudelman", "category": "ACTOR", "gender": "male"},
    "עידן עמדי": {"en": "Idan Amedi", "category": "ACTOR", "gender": "male"},
    "עידן ריכל": {"en": "Idan Raichel", "category": "VOICE", "gender": "male"},
    "קטרין נימני": {"en": "Katrin Nimni", "category": "MODEL", "gender": "female"},
    "רביב דרוקר": {"en": "Raviv Drucker", "category": "PRESENTER", "gender": "male"},
    "רומי פרנקל": {"en": "Romi Frenkel", "category": "ACTOR", "gender": "female"},
    "רותם סלע": {"en": "Rotem Sela", "category": "ACTOR", "gender": "female"},
    "שולי ראנד": {"en": "Shuli Rand", "category": "ACTOR", "gender": "male"},
    "שחר חיון": {"en": "Shahar Hasson", "category": "ACTOR", "gender": "male"},
    "שרון גל": {"en": "Sharon Gal", "category": "PRESENTER", "gender": "male"},
}

# Actor bios
ACTOR_BIOS = {
    "Gal Gadot": "Israeli actress and model, best known for her role as Wonder Woman in the DC Extended Universe. Former Miss Israel and IDF combat instructor.",
    "Bar Refaeli": "Israeli supermodel and television host. One of the world's most recognized models, known for Sports Illustrated covers and international campaigns.",
    "Noa Kirel": "Israeli singer, songwriter, and television personality. Multi-platinum recording artist and Eurovision 2023 third-place finisher.",
    "Lior Raz": "Israeli actor, screenwriter and producer. Creator and star of the hit series 'Fauda'. Former IDF special forces.",
    "Yehuda Levi": "Israeli actor known for his roles in 'Yossi & Jagger' and various Israeli TV series. Acclaimed dramatic performer.",
    "Omer Adam": "Israeli singer and songwriter. One of Israel's most popular musicians with multiple platinum albums.",
    "Idan Raichel": "Israeli musician, composer and arranger. Founder of 'The Idan Raichel Project', blending world music with Israeli sounds.",
    "Rotem Sela": "Israeli actress, model, and television host. Known for roles in Israeli cinema and as a beauty brand ambassador.",
    "Anna Zak": "Israeli singer and social media influencer. Popular content creator with millions of followers across platforms.",
    "Yael Shelbia": "Israeli model ranked among world's most beautiful faces. International fashion model and social media personality.",
    "Danny Kushmaro": "Israeli journalist and news anchor. Award-winning broadcaster and face of Israeli evening news.",
    "Idan Amedi": "Israeli actor and singer. Star of 'Fauda' and accomplished musician with chart-topping singles.",
    "Shuli Rand": "Israeli actor, singer and screenwriter. Known for 'Ushpizin' which he wrote and starred in.",
    "Shahar Hasson": "Israeli actor known for comedy and drama roles in Israeli television and film.",
    "Raviv Drucker": "Israeli investigative journalist and political commentator. Known for hard-hitting political reporting.",
}

PRICING_TIERS = [
    {"name": "Basic", "price": 99, "features": ["10 AI-generated images", "Personal use only", "Standard resolution"]},
    {"name": "Professional", "price": 299, "features": ["50 AI-generated images", "Commercial use", "High resolution", "Priority processing"]},
    {"name": "Enterprise", "price": 999, "features": ["Unlimited images", "Full commercial rights", "4K resolution", "Voice cloning", "Priority support"]}
]


def slugify(name: str) -> str:
    """Create URL-friendly slug from name"""
    return name.lower().replace(" ", "-").replace("'", "")


def get_s3_client():
    """Get S3/MinIO client"""
    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    )
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=config,
        region_name="us-east-1",
    )


def upload_image(s3_client, image_path: Path, actor_slug: str) -> str:
    """Upload image to S3/MinIO"""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = image_path.suffix.lower()
    content_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/jpeg")

    filename = f"actors/{actor_slug}/profile{ext}"

    # Ensure bucket exists
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
    except:
        s3_client.create_bucket(Bucket=S3_BUCKET)

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=filename,
        Body=image_bytes,
        ContentType=content_type,
    )

    return f"{S3_ENDPOINT}/{S3_BUCKET}/{filename}"


async def main():
    print("\n" + "="*60)
    print("  ActorHub.ai - Israeli Actors Seeder")
    print("="*60 + "\n")

    # Connect to database
    conn = await asyncpg.connect(DB_URL)
    print("Connected to database")

    # Setup S3
    s3_client = get_s3_client()
    print("Connected to S3/MinIO\n")

    # Find actors directory
    actors_dir = Path(r"C:\ActorHub.ai 1.1\שחקנים")
    if not actors_dir.exists():
        print(f"ERROR: Actors directory not found: {actors_dir}")
        return

    image_files = list(actors_dir.glob("*.jpg")) + list(actors_dir.glob("*.jpeg")) + list(actors_dir.glob("*.png"))
    print(f"Found {len(image_files)} actor images\n")

    # Get or create admin user
    admin_row = await conn.fetchrow("SELECT id FROM users WHERE email = 'admin@actorhub.ai'")
    if admin_row:
        admin_id = admin_row["id"]
        print(f"Found existing admin user: {admin_id}")
    else:
        admin_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO users (id, email, display_name, role, is_active, is_verified, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, admin_id, "admin@actorhub.ai", "ActorHub Admin", "admin", True, True, datetime.utcnow())
        print(f"Created admin user: {admin_id}")

    success_count = 0
    skip_count = 0
    error_count = 0

    for image_path in image_files:
        hebrew_name = image_path.stem

        if hebrew_name not in ACTOR_NAMES:
            print(f"  SKIP: Unknown actor '{hebrew_name}'")
            skip_count += 1
            continue

        actor_info = ACTOR_NAMES[hebrew_name]
        name_en = actor_info["en"]
        category = actor_info["category"]
        slug = slugify(name_en)

        try:
            print(f"  Processing: {hebrew_name} -> {name_en}")

            # Check if already exists
            existing = await conn.fetchrow(
                "SELECT id FROM identities WHERE user_id = $1 AND display_name = $2",
                admin_id, name_en
            )
            if existing:
                print(f"    - Already exists, skipping\n")
                skip_count += 1
                continue

            # 1. Upload image
            image_url = upload_image(s3_client, image_path, slug)
            print(f"    - Uploaded image")

            # 2. Create identity
            identity_id = uuid.uuid4()
            bio = ACTOR_BIOS.get(name_en, f"Israeli {category.lower()} - {name_en}")

            await conn.execute("""
                INSERT INTO identities (
                    id, user_id, display_name, bio, profile_image_url,
                    status, verified_at, verification_method, protection_level,
                    allow_commercial_use, allow_ai_training, show_in_public_gallery,
                    base_license_fee, per_image_rate, revenue_share_percent, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                identity_id, admin_id, name_en, bio, image_url,
                "VERIFIED", datetime.utcnow(), "admin", "PRO",
                True, True, True,
                99.0, 5.0, 70.0, datetime.utcnow()
            )
            print(f"    - Created identity")

            # 3. Create actor pack
            actor_pack_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO actor_packs (
                    id, identity_id, name, description, version, slug,
                    training_status, training_completed_at, training_progress,
                    quality_score, authenticity_score, consistency_score,
                    is_public, is_available, base_price_usd, price_per_image_usd, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            """,
                actor_pack_id, identity_id, f"{name_en} Actor Pack",
                f"AI-ready digital likeness of {name_en}. Generate images, voice, and motion content.",
                "1.0.0", slug,
                "COMPLETED", datetime.utcnow(), 100,
                95.0, 92.0, 90.0,
                True, True, 99.0, 5.0, datetime.utcnow()
            )
            print(f"    - Created actor pack")

            # 4. Create marketplace listing
            listing_id = uuid.uuid4()
            tags = ["israeli", category.lower(), "celebrity", "verified"]
            style_tags = ["professional", "versatile"]

            await conn.execute("""
                INSERT INTO listings (
                    id, identity_id, title, slug, description, short_description,
                    thumbnail_url, preview_images, category, tags, style_tags,
                    pricing_tiers, is_active, is_featured, created_at, published_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                listing_id, identity_id, name_en, slug, bio,
                f"Premium AI Actor Pack for {name_en}",
                image_url, [image_url], category, tags, style_tags,
                json.dumps(PRICING_TIERS), True, category in ["ACTOR", "MODEL"],
                datetime.utcnow(), datetime.utcnow()
            )
            print(f"    - Created marketplace listing")

            success_count += 1
            print(f"    SUCCESS!\n")

        except Exception as e:
            error_count += 1
            print(f"    ERROR: {e}\n")
            continue

    await conn.close()

    # Summary
    print("\n" + "="*60)
    print("  Summary")
    print("="*60)
    print(f"  Successfully added: {success_count}")
    print(f"  Skipped:            {skip_count}")
    print(f"  Errors:             {error_count}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
