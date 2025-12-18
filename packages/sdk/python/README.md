# ActorHub.ai Python SDK

Official Python SDK for ActorHub.ai - Digital Identity Protection Platform.

## Installation

```bash
pip install actorhub
```

## Quick Start

```python
from actorhub import ActorHub

# Initialize client
client = ActorHub(api_key="your_api_key")

# Check if an image contains protected identities
result = client.verify(image_url="https://example.com/face.jpg")

if result.protected:
    print(f"Protected identity found: {result.identities[0].display_name}")
    print(f"License required: {result.identities[0].license_required}")
else:
    print("No protected identities detected")
```

## Features

- **Identity Verification**: Check if images contain protected identities
- **License Management**: Purchase and manage licenses programmatically
- **Actor Pack Downloads**: Download licensed Actor Packs for content generation
- **Async Support**: Full async/await support with `AsyncActorHub`

## Usage Examples

### Verify an Image

```python
from actorhub import ActorHub

client = ActorHub(api_key="your_api_key")

# From URL
result = client.verify(image_url="https://example.com/image.jpg")

# From base64
result = client.verify(image_base64="...")

# From file
with open("image.jpg", "rb") as f:
    result = client.verify(image_bytes=f.read())

print(f"Faces detected: {result.faces_detected}")
print(f"Protected: {result.protected}")

for identity in result.identities:
    if identity.protected:
        print(f"  - {identity.display_name} (score: {identity.similarity_score:.2f})")
```

### Purchase a License

```python
# Get pricing
price = client.get_license_price(
    identity_id="uuid",
    license_type="commercial",
    usage_type="subscription",
    duration_days=30
)
print(f"Total price: ${price['total_price']}")

# Purchase
license = client.purchase_license(
    identity_id="uuid",
    license_type="commercial",
    usage_type="subscription",
    duration_days=30
)
print(f"License ID: {license.id}")
```

### Download Actor Pack

```python
# Download to file
path = client.download_actor_pack(
    identity_id="uuid",
    output_path="actor_pack.zip"
)
print(f"Downloaded to: {path}")
```

### Async Usage

```python
import asyncio
from actorhub import AsyncActorHub

async def main():
    async with AsyncActorHub(api_key="your_api_key") as client:
        result = await client.verify(image_url="https://example.com/face.jpg")
        print(f"Protected: {result.protected}")

asyncio.run(main())
```

## Integration Examples

### With Sora/Kling

```python
from actorhub import ActorHub

client = ActorHub(api_key="your_api_key")

def check_before_generate(prompt_image_url: str) -> dict:
    """Check if image contains protected identities before AI generation."""
    result = client.verify(image_url=prompt_image_url)

    if result.protected:
        # Get the first protected identity
        identity = result.identities[0]

        if identity.license_required:
            return {
                "allowed": False,
                "reason": "Protected identity requires license",
                "identity": identity.display_name,
                "license_url": f"https://actorhub.ai/license/{identity.identity_id}"
            }

        # Check blocked categories
        if "adult" in identity.blocked_categories:
            return {
                "allowed": False,
                "reason": "Identity blocks adult content"
            }

    return {"allowed": True}
```

## API Reference

### ActorHub

```python
class ActorHub:
    def __init__(self, api_key: str, base_url: str = "https://api.actorhub.ai/v1")

    def verify(
        self,
        image_url: str = None,
        image_base64: str = None,
        image_bytes: bytes = None
    ) -> VerifyResponse

    def get_license_price(
        self,
        identity_id: str,
        license_type: str,
        usage_type: str,
        duration_days: int = 30
    ) -> dict

    def purchase_license(
        self,
        identity_id: str,
        license_type: str,
        usage_type: str,
        duration_days: int = 30
    ) -> License

    def download_actor_pack(
        self,
        identity_id: str,
        output_path: str = None
    ) -> str
```

## License

MIT License - see LICENSE file for details.
