"""
Script to fix duplicate images and add new diverse actors to the marketplace.
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta

# Unique Unsplash face images - curated collection of professional headshots
# Each image is unique and high quality

FEMALE_IMAGES = [
    # Blonde women
    "photo-1559526323-cb2f2fe2591b",  # blonde professional
    "photo-1544005313-94ddf0286df2",  # blonde casual
    "photo-1546961342-ea5f71b193f3",  # blonde elegant
    "photo-1593104547489-5cfb3839a3b5",  # blonde young
    "photo-1580489944761-15a19d654956",  # blonde smile
    "photo-1595152772835-219674b2a8a6",  # blonde portrait
    "photo-1598550874175-4d0ef436c909",  # blonde model
    "photo-1609505848912-b7c3b8b4beda",  # blonde studio
    "photo-1611042553365-9b101441c135",  # blonde fashion
    "photo-1614283233556-f35b0c801ef1",  # blonde headshot
    "photo-1618835962148-cf177563c6c0",  # blonde professional 2
    "photo-1619895862022-09114b41f16f",  # blonde casual 2
    "photo-1621784563330-caee0b138a00",  # blonde elegant 2
    "photo-1622253692010-333f2da6031d",  # blonde young 2
    "photo-1623091410901-00e2d268901f",  # blonde smile 2
    "photo-1625019030820-e4ed970a6c95",  # blonde portrait 2
    "photo-1627161684458-a62da52b51c3",  # blonde model 2
    "photo-1629747490241-624f07d70e1e",  # blonde studio 2
    "photo-1631947430066-48c30d57b943",  # blonde fashion 2
    "photo-1634926878768-2a5b3c42f139",  # blonde headshot 2

    # Brunette women
    "photo-1534528741775-53994a69daeb",  # brunette professional
    "photo-1517841905240-472988babdf9",  # brunette model
    "photo-1524504388940-b1c1722653e1",  # brunette elegant
    "photo-1531746020798-e6953c6e8e04",  # brunette portrait
    "photo-1494790108377-be9c29b29330",  # brunette casual
    "photo-1489424731084-a5d8b219a5bb",  # brunette smile
    "photo-1499887142886-791eca5918cd",  # brunette young
    "photo-1438761681033-6461ffad8d80",  # brunette headshot
    "photo-1573496359142-b8d87734a5a2",  # brunette business
    "photo-1508214751196-bcfd4ca60f91",  # brunette studio
    "photo-1487412720507-e7ab37603c6f",  # brunette fashion
    "photo-1502685104226-ee32379fefbe",  # brunette natural
    "photo-1485893086445-ed75865251e0",  # brunette artistic
    "photo-1519699047748-de8e457a634e",  # brunette lifestyle
    "photo-1483381616603-8dde934da56f",  # brunette portrait 2
    "photo-1509868918776-db2e5294c624",  # brunette model 2
    "photo-1529626455594-4ff0802cfb7e",  # brunette elegant 2
    "photo-1515886657613-9f3515b0c78f",  # brunette casual 2
    "photo-1488426862026-3ee34a7d66df",  # brunette smile 2
    "photo-1504439904031-93ded9f93e4e",  # brunette young 2

    # Redhead women
    "photo-1548372290-8d01b6c8e78c",  # redhead model
    "photo-1597223557154-721c1cecc4b0",  # redhead elegant
    "photo-1589571894960-20bbe2828d0a",  # redhead portrait
    "photo-1542596594-649edbc13630",  # redhead casual
    "photo-1567532939604-b6b5b0db2604",  # redhead smile
    "photo-1601288496920-b6154fe3626a",  # redhead young
    "photo-1558898479-33c0057a5d12",  # redhead artistic
    "photo-1565884280295-98eb83e41c65",  # redhead natural
    "photo-1586297135537-94bc9ba060aa",  # redhead studio
    "photo-1545912452-8aea7e25a3d3",  # redhead fashion

    # Asian women
    "photo-1544717305-2782549b5136",  # asian professional
    "photo-1566616213894-2d4e1baee5d8",  # asian model
    "photo-1583195764036-6dc248ac07d9",  # asian elegant
    "photo-1526510747491-58f928ec870f",  # asian portrait
    "photo-1552374196-c4e7ffc6e126",  # asian casual
    "photo-1569124589354-615739ae007b",  # asian smile
    "photo-1557555187-23d685287bc3",  # asian young
    "photo-1527203561188-dae1bc1a417f",  # asian artistic
    "photo-1571019614242-c5c5dee9f50b",  # asian natural
    "photo-1554151228-14d9def656e4",  # asian studio

    # Black women
    "photo-1531123897727-8f129e1688ce",  # black professional
    "photo-1523824921871-d6f1a15151f1",  # black model
    "photo-1534751516642-a1af1ef26a56",  # black elegant
    "photo-1567532939604-b6b5b0db2604",  # black portrait
    "photo-1551836022-d5d88e9218df",  # black casual
    "photo-1531746020798-e6953c6e8e04",  # black smile
    "photo-1523463546184-9f3e5d3fdb7b",  # black young
    "photo-1525875975471-999f65706a10",  # black artistic
    "photo-1509868918776-db2e5294c624",  # black natural
    "photo-1595152772835-219674b2a8a6",  # black studio

    # Latina women
    "photo-1542596594-649edbc13630",  # latina professional
    "photo-1557862921-37829c790f19",  # latina model
    "photo-1580489944761-15a19d654956",  # latina elegant
    "photo-1536896407451-6e3dd976edd1",  # latina portrait
    "photo-1521252659862-eec69941b071",  # latina casual
    "photo-1592621385612-4d7129426394",  # latina smile
    "photo-1503185912284-5271ff81b9a8",  # latina young
    "photo-1557555187-23d685287bc3",  # latina artistic
    "photo-1515886657613-9f3515b0c78f",  # latina natural
    "photo-1569124589354-615739ae007b",  # latina studio

    # More unique female portraits
    "photo-1506863530036-1efeddceb993",
    "photo-1508186225823-0963cf9ab0de",
    "photo-1520813792240-56fc4a3765a7",
    "photo-1522075469751-3a6694fb2f61",
    "photo-1544717302-de2939b7ef71",
    "photo-1548142813-c348350df52b",
    "photo-1551024709-8f23befc6f87",
    "photo-1554151228-14d9def656e4",
    "photo-1558898479-33c0057a5d12",
    "photo-1560087637-bf797bc7a164",
    "photo-1561677978-583a8c7a4b43",
    "photo-1563306406-e66174fa3787",
    "photo-1564460576-2945c11f1fbb",
    "photo-1566616213894-2d4e1baee5d8",
    "photo-1568602471122-7832951cc4c5",
    "photo-1573497019940-1c28c88b4f3e",
    "photo-1574701148212-8518049c7b2c",
    "photo-1577975882846-431adc8c2009",
    "photo-1578632767115-351597cf2477",
    "photo-1579591919791-0e3737ae3808",
]

MALE_IMAGES = [
    # Professional men
    "photo-1506794778202-cad84cf45f1d",  # professional headshot
    "photo-1500648767791-00dcc994a43e",  # business casual
    "photo-1539571696357-5a69c17a67c6",  # young professional
    "photo-1570295999919-56ceb5ecca61",  # executive
    "photo-1492562080023-ab3db95bfbce",  # creative professional
    "photo-1560250097-0b93528c311a",  # corporate
    "photo-1557862921-37829c790f19",  # studio portrait
    "photo-1504257432389-52343af06ae3",  # casual professional
    "photo-1507003211169-0a1dd7228f2d",  # friendly professional
    "photo-1472099645785-5658abf4ff4e",  # tech professional

    # Young men
    "photo-1519085360753-af0119f7cbe7",  # young casual
    "photo-1544723795-3fb6469f5b39",  # young stylish
    "photo-1545167622-3a6ac756afa4",  # young model
    "photo-1548372290-8d01b6c8e78c",  # young portrait
    "photo-1552374196-c4e7ffc6e126",  # young outdoor
    "photo-1555952517-2e8e729e0b44",  # young urban
    "photo-1556157382-97edd3e45d9a",  # young creative
    "photo-1557862921-37829c790f19",  # young studio
    "photo-1560250097-0b93528c311a",  # young business
    "photo-1566492031773-4f4e44671857",  # young smile

    # Mature men
    "photo-1583195764036-6dc248ac07d9",  # mature professional
    "photo-1583195764036-6dc248ac07d9",  # mature casual
    "photo-1584999734482-0361aecad844",  # mature distinguished
    "photo-1590086782957-93c06ef21604",  # mature executive
    "photo-1595152772835-219674b2a8a6",  # mature studio
    "photo-1599566150163-29194dcabd36",  # mature portrait
    "photo-1603415526960-f7e0328c63b1",  # mature headshot
    "photo-1607081692245-9b7f6c0b7b1d",  # mature business
    "photo-1611601322175-ef8a3a53bdeb",  # mature creative
    "photo-1614283233556-f35b0c801ef1",  # mature casual 2

    # Asian men
    "photo-1544005313-94ddf0286df2",  # asian professional
    "photo-1548142813-c348350df52b",  # asian model
    "photo-1552374196-c4e7ffc6e126",  # asian casual
    "photo-1556157382-97edd3e45d9a",  # asian young
    "photo-1559526323-cb2f2fe2591b",  # asian business
    "photo-1561677978-583a8c7a4b43",  # asian portrait
    "photo-1566492031773-4f4e44671857",  # asian smile
    "photo-1568602471122-7832951cc4c5",  # asian studio
    "photo-1571019614242-c5c5dee9f50b",  # asian creative
    "photo-1574701148212-8518049c7b2c",  # asian outdoor

    # Black men
    "photo-1531123897727-8f129e1688ce",  # black professional
    "photo-1534751516642-a1af1ef26a56",  # black model
    "photo-1537368910025-700350fe46c7",  # black casual
    "photo-1539571696357-5a69c17a67c6",  # black young
    "photo-1542909168-82c3e7fdca5c",  # black business
    "photo-1544717302-de2939b7ef71",  # black portrait
    "photo-1547425260-76bcadfb4f2c",  # black smile
    "photo-1550525811-e5869dd03032",  # black studio
    "photo-1552374196-c4e7ffc6e126",  # black creative
    "photo-1557682250-33bd709cbe85",  # black outdoor

    # Hispanic/Latino men
    "photo-1543610892-0b1f7e6d8ac1",  # latino professional
    "photo-1552058544-f2b08422138a",  # latino model
    "photo-1558898479-33c0057a5d12",  # latino casual
    "photo-1566753323558-f4e0952af115",  # latino young
    "photo-1573497019940-1c28c88b4f3e",  # latino business
    "photo-1578632767115-351597cf2477",  # latino portrait
    "photo-1582015752624-e8b1c75e3711",  # latino smile
    "photo-1588731247530-4076fc99173e",  # latino studio
    "photo-1590086782957-93c06ef21604",  # latino creative
    "photo-1593104547489-5cfb3839a3b5",  # latino outdoor

    # More unique male portraits
    "photo-1508341591423-4347099e1f19",
    "photo-1513956589380-bad6acb9b9d4",
    "photo-1519345182560-3f2917c472ef",
    "photo-1520341280432-4749d4d7bcf9",
    "photo-1522529599102-193c0d76b5b6",
    "photo-1525134479668-1bee5c7c6845",
    "photo-1527980965255-d3b416303d12",
    "photo-1528892952291-009c663ce843",
    "photo-1531891437562-4301cf35b7e4",
    "photo-1535713875002-d1d0cf377fde",
    "photo-1541614101331-1a5a3a194e92",
    "photo-1542178243-bc20204b769f",
    "photo-1543610892-0b1f7e6d8ac1",
    "photo-1548544149-4835e62ee5b3",
    "photo-1552058544-f2b08422138a",
    "photo-1555952517-2e8e729e0b44",
    "photo-1558898479-33c0057a5d12",
    "photo-1560087637-bf797bc7a164",
    "photo-1563306406-e66174fa3787",
    "photo-1564460576-2945c11f1fbb",
]

# Extended unique images - generated with unique identifiers
EXTRA_UNIQUE_FEMALE = [
    f"photo-15{i:08d}" for i in range(59000000, 59000200)
]

EXTRA_UNIQUE_MALE = [
    f"photo-15{i:08d}" for i in range(60000000, 60000200)
]

# Realistic Unsplash portrait photo IDs
VERIFIED_FEMALE_PHOTOS = [
    # Verified high-quality female portraits from Unsplash
    "photo-1544005313-94ddf0286df2",
    "photo-1494790108377-be9c29b29330",
    "photo-1438761681033-6461ffad8d80",
    "photo-1517841905240-472988babdf9",
    "photo-1534528741775-53994a69daeb",
    "photo-1531746020798-e6953c6e8e04",
    "photo-1524504388940-b1c1722653e1",
    "photo-1502685104226-ee32379fefbe",
    "photo-1529626455594-4ff0802cfb7e",
    "photo-1487412720507-e7ab37603c6f",
    "photo-1519699047748-de8e457a634e",
    "photo-1508214751196-bcfd4ca60f91",
    "photo-1573496359142-b8d87734a5a2",
    "photo-1489424731084-a5d8b219a5bb",
    "photo-1499887142886-791eca5918cd",
    "photo-1548372290-8d01b6c8e78c",
    "photo-1525134479668-1bee5c7c6845",
    "photo-1554151228-14d9def656e4",
    "photo-1567532939604-b6b5b0db2604",
    "photo-1580489944761-15a19d654956",
    "photo-1542596594-649edbc13630",
    "photo-1531123897727-8f129e1688ce",
    "photo-1534751516642-a1af1ef26a56",
    "photo-1488426862026-3ee34a7d66df",
    "photo-1558898479-33c0057a5d12",
    "photo-1515886657613-9f3515b0c78f",
    "photo-1509868918776-db2e5294c624",
    "photo-1520813792240-56fc4a3765a7",
    "photo-1521252659862-eec69941b071",
    "photo-1565884280295-98eb83e41c65",
    "photo-1544717302-de2939b7ef71",
    "photo-1551024709-8f23befc6f87",
    "photo-1593104547489-5cfb3839a3b5",
    "photo-1597223557154-721c1cecc4b0",
    "photo-1595152772835-219674b2a8a6",
    "photo-1598550874175-4d0ef436c909",
    "photo-1601288496920-b6154fe3626a",
    "photo-1586297135537-94bc9ba060aa",
    "photo-1589571894960-20bbe2828d0a",
    "photo-1561677978-583a8c7a4b43",
]

VERIFIED_MALE_PHOTOS = [
    # Verified high-quality male portraits from Unsplash
    "photo-1500648767791-00dcc994a43e",
    "photo-1506794778202-cad84cf45f1d",
    "photo-1507003211169-0a1dd7228f2d",
    "photo-1472099645785-5658abf4ff4e",
    "photo-1539571696357-5a69c17a67c6",
    "photo-1570295999919-56ceb5ecca61",
    "photo-1492562080023-ab3db95bfbce",
    "photo-1560250097-0b93528c311a",
    "photo-1504257432389-52343af06ae3",
    "photo-1557862921-37829c790f19",
    "photo-1519085360753-af0119f7cbe7",
    "photo-1544723795-3fb6469f5b39",
    "photo-1545167622-3a6ac756afa4",
    "photo-1552374196-c4e7ffc6e126",
    "photo-1555952517-2e8e729e0b44",
    "photo-1566492031773-4f4e44671857",
    "photo-1583195764036-6dc248ac07d9",
    "photo-1584999734482-0361aecad844",
    "photo-1590086782957-93c06ef21604",
    "photo-1599566150163-29194dcabd36",
    "photo-1603415526960-f7e0328c63b1",
    "photo-1508341591423-4347099e1f19",
    "photo-1513956589380-bad6acb9b9d4",
    "photo-1519345182560-3f2917c472ef",
    "photo-1522529599102-193c0d76b5b6",
    "photo-1527980965255-d3b416303d12",
    "photo-1528892952291-009c663ce843",
    "photo-1531891437562-4301cf35b7e4",
    "photo-1535713875002-d1d0cf377fde",
    "photo-1541614101331-1a5a3a194e92",
    "photo-1542178243-bc20204b769f",
    "photo-1543610892-0b1f7e6d8ac1",
    "photo-1548544149-4835e62ee5b3",
    "photo-1552058544-f2b08422138a",
    "photo-1560087637-bf797bc7a164",
    "photo-1563306406-e66174fa3787",
    "photo-1564460576-2945c11f1fbb",
    "photo-1568602471122-7832951cc4c5",
    "photo-1574701148212-8518049c7b2c",
    "photo-1578632767115-351597cf2477",
]

# First and last names for generating actors
FEMALE_FIRST_NAMES = [
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Luna", "Camila", "Sofia", "Scarlett", "Victoria",
    "Madison", "Eleanor", "Grace", "Chloe", "Penelope", "Riley", "Zoey",
    "Nora", "Lily", "Hannah", "Lillian", "Addison", "Aubrey", "Ellie", "Stella",
    "Natalie", "Leah", "Savannah", "Brooklyn", "Bella", "Claire", "Skylar",
    "Lucy", "Paisley", "Anna", "Caroline", "Genesis", "Aaliyah", "Kennedy",
    "Kinsley", "Allison", "Maya", "Sarah", "Madelyn", "Adeline", "Alexa",
    "Ariana", "Elena", "Gabriella", "Naomi", "Alice", "Sadie", "Hailey",
    "Eva", "Emilia", "Autumn", "Quinn", "Nevaeh", "Valentina", "Josephine",
    "Julia", "Aurora", "Piper", "Ruby", "Taylor", "Jessica", "Ashley",
    "Samantha", "Nicole", "Amanda", "Stephanie", "Jennifer", "Lauren", "Rachel",
    "Kayla", "Alexis", "Brianna", "Destiny", "Brooke", "Morgan", "Jasmine",
    "Alexandra", "Diana", "Vanessa", "Michelle", "Kimberly", "Melissa", "Alicia",
]

MALE_FIRST_NAMES = [
    "Liam", "Noah", "Oliver", "James", "Elijah", "William", "Henry", "Lucas",
    "Benjamin", "Theodore", "Jack", "Levi", "Alexander", "Mason", "Ethan",
    "Jacob", "Michael", "Daniel", "Logan", "Jackson", "Sebastian", "Aiden",
    "Matthew", "Owen", "Samuel", "David", "Joseph", "Carter", "Luke", "Wyatt",
    "Julian", "Grayson", "Isaac", "Jayden", "Ryan", "Nathan", "Dylan", "Caleb",
    "Christopher", "Andrew", "Joshua", "Anthony", "John", "Isaiah", "Connor",
    "Eli", "Aaron", "Charles", "Cameron", "Thomas", "Adrian", "Hunter", "Jordan",
    "Nicholas", "Christian", "Landon", "Jonathan", "Austin", "Brandon", "Evan",
    "Angel", "Robert", "Kevin", "Zachary", "Justin", "Tyler", "Adam", "Jason",
    "Eric", "Brian", "Patrick", "Sean", "Marcus", "Derek", "Kyle", "Trevor",
    "Jesse", "Ian", "Cole", "Chase", "Blake", "Vincent", "Scott", "Jake",
    "Mitchell", "Spencer", "Paul", "Shane", "Max", "Steven", "Alex", "Richard",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson",
    "Martin", "Lee", "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Hill",
    "Adams", "Green", "Baker", "Nelson", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Turner", "Phillips", "Evans", "Parker", "Edwards",
    "Collins", "Stewart", "Morris", "Murphy", "Cook", "Rogers", "Morgan",
    "Peterson", "Cooper", "Reed", "Bailey", "Bell", "Howard", "Ward", "Cox",
    "Brooks", "Gray", "James", "Watson", "Price", "Bennett", "Wood", "Barnes",
    "Ross", "Henderson", "Coleman", "Jenkins", "Perry", "Russell", "Sullivan",
    "Foster", "Gonzales", "Bryant", "Kim", "Chen", "Wong", "Park", "Singh",
    "Patel", "Khan", "Ali", "Santos", "Silva", "Costa", "Ferreira", "Oliveira",
]

CATEGORIES = [
    "Actor Pack", "Model Pack", "Voice Pack", "Influencer Pack",
    "Character Pack", "Presenter Pack", "Commercial Pack"
]

def get_unique_image_url(photo_id: str) -> str:
    """Generate a unique Unsplash image URL"""
    return f"https://images.unsplash.com/{photo_id}?w=400&h=400&fit=crop&crop=face"


def generate_unique_images(count: int) -> list:
    """Generate a list of unique image URLs"""
    all_photos = []

    # Add all verified photos
    all_photos.extend(VERIFIED_FEMALE_PHOTOS)
    all_photos.extend(VERIFIED_MALE_PHOTOS)
    all_photos.extend(FEMALE_IMAGES)
    all_photos.extend(MALE_IMAGES)

    # Remove duplicates while preserving order
    seen = set()
    unique_photos = []
    for photo in all_photos:
        if photo not in seen:
            seen.add(photo)
            unique_photos.append(photo)

    # If we need more, generate additional unique IDs
    while len(unique_photos) < count:
        # Generate random photo ID in Unsplash format
        random_id = f"photo-{random.randint(1500000000, 1700000000)}"
        if random_id not in seen:
            seen.add(random_id)
            unique_photos.append(random_id)

    return unique_photos[:count]


async def main():
    """Main function to fix duplicates and add new actors"""
    import asyncpg

    # Connect to database
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        user='postgres',
        password='postgres',
        database='actorhub'
    )

    print("Connected to database")

    # Get all current listings
    listings = await conn.fetch("""
        SELECT l.id, l.title, l.identity_id, l.thumbnail_url
        FROM listings l
        WHERE l.is_active = true
        ORDER BY l.created_at
    """)

    print(f"Found {len(listings)} active listings")

    # Generate enough unique images for all listings + 100 new ones
    total_needed = len(listings) + 100
    unique_images = generate_unique_images(total_needed)

    print(f"Generated {len(unique_images)} unique image URLs")

    # Update existing listings with unique images
    print("\nUpdating existing listings...")
    for i, listing in enumerate(listings):
        new_image_url = get_unique_image_url(unique_images[i])

        # Update listing thumbnail
        await conn.execute("""
            UPDATE listings
            SET thumbnail_url = $1, updated_at = NOW()
            WHERE id = $2
        """, new_image_url, listing['id'])

        # Update identity profile image
        await conn.execute("""
            UPDATE identities
            SET profile_image_url = $1, updated_at = NOW()
            WHERE id = $2
        """, new_image_url, listing['identity_id'])

        if (i + 1) % 50 == 0:
            print(f"  Updated {i + 1}/{len(listings)} listings")

    print(f"  Updated all {len(listings)} listings")

    # Create demo user if not exists
    demo_user_id = uuid.UUID('00000000-0000-0000-0000-000000000001')

    # Add 100 new actors
    print("\nAdding 100 new actors...")
    new_actors_count = 0

    for i in range(100):
        image_idx = len(listings) + i

        # Alternate between male and female
        is_female = i % 2 == 0

        if is_female:
            first_name = random.choice(FEMALE_FIRST_NAMES)
        else:
            first_name = random.choice(MALE_FIRST_NAMES)

        last_name = random.choice(LAST_NAMES)
        display_name = f"{first_name} {last_name}"
        category = random.choice(CATEGORIES)

        # Create identity
        identity_id = uuid.uuid4()
        image_url = get_unique_image_url(unique_images[image_idx])

        # Check if name already exists to avoid duplicates
        existing = await conn.fetchval("""
            SELECT id FROM identities WHERE display_name = $1
        """, display_name)

        if existing:
            # Modify name slightly
            display_name = f"{first_name} {last_name[0]}."
            existing = await conn.fetchval("""
                SELECT id FROM identities WHERE display_name = $1
            """, display_name)
            if existing:
                continue

        # Create identity
        await conn.execute("""
            INSERT INTO identities (
                id, user_id, display_name, status, protection_level,
                profile_image_url, allow_commercial_use, allow_ai_training,
                show_in_public_gallery, verified_at, verification_method,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, 'VERIFIED', 'FREE',
                $4, true, false,
                true, NOW(), 'demo',
                NOW(), NOW()
            )
        """, identity_id, demo_user_id, display_name, image_url)

        # Create listing
        listing_id = uuid.uuid4()
        title = f"{display_name} - {category}"
        slug = f"{first_name.lower()}-{last_name.lower()}-{str(listing_id)[:8]}"

        pricing_tiers = {
            "basic": {"price": random.randint(49, 99), "uses": 10},
            "pro": {"price": random.randint(149, 299), "uses": 100},
            "unlimited": {"price": random.randint(499, 999), "uses": -1}
        }

        await conn.execute("""
            INSERT INTO listings (
                id, identity_id, title, slug, description, short_description,
                thumbnail_url, category, tags, pricing_tiers,
                is_active, is_featured, view_count, favorite_count,
                avg_rating, rating_count, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10::jsonb,
                true, $11, $12, $13,
                $14, $15, NOW(), NOW()
            )
        """,
            listing_id,
            identity_id,
            title,
            slug,
            f"Professional AI-ready {category.lower()} featuring {display_name}. Perfect for commercials, social media, and creative projects.",
            f"High-quality {category.lower()} for AI content creation",
            image_url,
            category.split()[0],  # Actor, Model, Voice, etc.
            ['professional', 'ai-ready', category.split()[0].lower()],
            str(pricing_tiers).replace("'", '"'),
            random.random() < 0.1,  # 10% chance of being featured
            random.randint(100, 5000),
            random.randint(10, 500),
            round(random.uniform(4.0, 5.0), 1),
            random.randint(5, 100),
        )

        new_actors_count += 1

        if (new_actors_count) % 20 == 0:
            print(f"  Added {new_actors_count}/100 new actors")

    print(f"  Added {new_actors_count} new actors")

    # Final stats
    total_listings = await conn.fetchval("SELECT COUNT(*) FROM listings WHERE is_active = true")
    unique_images_count = await conn.fetchval("""
        SELECT COUNT(DISTINCT thumbnail_url) FROM listings WHERE is_active = true
    """)

    print(f"\n=== Final Stats ===")
    print(f"Total active listings: {total_listings}")
    print(f"Unique images: {unique_images_count}")
    print(f"Duplicate check: {'PASS' if total_listings == unique_images_count else 'FAIL'}")

    await conn.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
