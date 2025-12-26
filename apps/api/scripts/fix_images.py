"""Fix listing images with high-quality modern portrait photos"""
import asyncio
import random
import httpx
from sqlalchemy import text

import sys
sys.path.insert(0, 'C:/ActorHub.ai 1.1/apps/api')

from app.core.database import async_session_maker

# High-quality modern Unsplash portraits - professionally shot
PORTRAIT_PHOTOS = [
    # High-quality women portraits
    '1494790108377-be9c29b29330',  # Professional blonde
    '1534528741775-53994a69daeb',  # Model headshot
    '1517841905240-472988babdf9',  # Blonde casual
    '1524504388940-b1c1722653e1',  # Professional woman
    '1438761681033-6461ffad8d80',  # Business woman
    '1544005313-94ddf0286df2',     # Studio portrait
    '1488426862026-3ee34a7d66df',  # Young professional
    '1531746020798-e6953c6e8e04',  # Artistic portrait
    '1508214751196-bcfd4ca60f91',  # Elegant woman
    '1573496359142-b8d87734a5a2',  # Business headshot
    '1573497019940-1c28c88b4f3e',  # Professional
    '1580489944761-15a19d654956',  # Natural beauty
    '1487412720507-e7ab37603c6f',  # Creative portrait
    '1502685104226-ee32379fefbe',  # Professional glasses
    '1489424731084-a5d8b219a5bb',  # Natural light
    '1546961342-ea5f71b193f3',     # Fashion portrait
    '1567532939604-b6b5b0db2604',  # Blonde professional
    '1544725176-7c40e5a71c5e',     # Studio shot
    '1581382575275-97901c2635b7',  # Modern portrait
    '1583195764036-6dc248ac07d9',  # Business portrait

    # High-quality men portraits
    '1507003211169-0a1dd7228f2d',  # Professional man
    '1472099645785-5658abf4ff4e',  # Business headshot
    '1506794778202-cad84cf45f1d',  # Studio portrait
    '1500648767791-00dcc994a43e',  # Smiling professional
    '1539571696357-5a69c17a67c6',  # Casual modern
    '1519085360753-af0119f7cbe7',  # Business professional
    '1492562080023-ab3db95bfbce',  # Modern portrait
    '1519345182560-3f2917c472ef',  # Professional
    '1527980965255-d3b416303d12',  # Studio shot
    '1504257432389-52343af06ae3',  # Close-up
    '1522075469751-3a6694fb2f61',  # Professional headshot
    '1552058544-f2b08422138a',     # Creative portrait
    '1560250097-0b93528c311a',     # Business
    '1507591064344-4c6ce005b128',  # Casual
    '1463453091185-61582044d556',  # Beard portrait
    '1542909168-82c3e7fdca5c',     # Close-up
    '1566492031773-4f4e44671857',  # Professional
    '1568602471122-7832951cc4c5',  # Modern
    '1587397845856-e6cf49176c70',  # Casual portrait
    '1553514029-1318c9127859',     # Studio
]

async def verify_and_fix():
    print('Verifying photos...')

    working = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for photo_id in PORTRAIT_PHOTOS:
            url = f'https://images.unsplash.com/photo-{photo_id}'
            try:
                resp = await client.head(url)
                if resp.status_code == 200:
                    working.append(photo_id)
                    print(f'  OK: {photo_id}')
                else:
                    print(f'  FAIL: {photo_id} ({resp.status_code})')
            except Exception as e:
                print(f'  ERR: {photo_id}')

    print(f'\n{len(working)} verified working photos')

    if len(working) < 10:
        print('ERROR: Not enough photos!')
        return

    async with async_session_maker() as db:
        result = await db.execute(text('SELECT id FROM listings WHERE is_active = true ORDER BY created_at'))
        listing_ids = [row[0] for row in result.fetchall()]

        print(f'Updating {len(listing_ids)} listings...')

        random.shuffle(working)

        for i, listing_id in enumerate(listing_ids):
            photo_id = working[i % len(working)]
            # High quality settings
            url = f'https://images.unsplash.com/photo-{photo_id}?w=500&h=500&fit=crop&crop=faces&q=90'

            await db.execute(
                text('UPDATE listings SET thumbnail_url = :url WHERE id = :id'),
                {'url': url, 'id': listing_id}
            )

        await db.commit()
        print(f'Done! {len(working)} unique high-quality portraits')

if __name__ == '__main__':
    asyncio.run(verify_and_fix())
