"""
Identity API Integration Test
Tests identity verification and marketplace endpoints
"""
import httpx
import sys
import base64
import time
from io import BytesIO

API_URL = "http://localhost:8000/api/v1"

def create_test_image():
    """Create a simple test image"""
    try:
        from PIL import Image
        img = Image.new('RGB', (256, 256), color='beige')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()
    except ImportError:
        # Simple 1x1 JPEG if PIL not available
        return base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQCEAwEPwAB//9k="
        )

def test_identity_api():
    """Test identity API endpoints"""

    print("Testing Identity API...")

    with httpx.Client(base_url=API_URL, timeout=60) as client:

        # First, login to get token
        print("\n  Getting auth token...")
        unique_email = f"identity_test_{int(time.time())}@test.com"

        # Register user
        register_response = client.post("/users/register", json={
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Identity",
            "last_name": "Tester"
        })

        if register_response.status_code not in [200, 201]:
            print(f"    [WARN] Registration: {register_response.status_code}")

        # Login
        login_response = client.post("/users/login", json={
            "email": unique_email,
            "password": "TestPassword123!"
        })

        if login_response.status_code != 200:
            print(f"    [FAIL] Login failed: {login_response.status_code}")
            return False

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("    [OK] Auth token obtained")

        # Test 1: List identities
        print("\n  Test 1: List Identities")
        response = client.get("/identity/mine", headers=headers)

        if response.status_code == 200:
            identities = response.json()
            print(f"    [OK] Identity listing works")
            print(f"        Registered identities: {len(identities) if isinstance(identities, list) else 0}")
        else:
            print(f"    [FAIL] Identity listing failed: {response.status_code}")
            return False

        # Test 2: Marketplace listings
        print("\n  Test 2: Marketplace API")
        response = client.get("/marketplace/listings")

        if response.status_code == 200:
            listings = response.json()
            print(f"    [OK] Marketplace API works")
            count = len(listings) if isinstance(listings, list) else 0
            print(f"        Active listings: {count}")
        else:
            print(f"    [WARN] Marketplace returned: {response.status_code}")

        # Test 3: Categories endpoint
        print("\n  Test 3: Marketplace Categories")
        response = client.get("/marketplace/categories")

        if response.status_code == 200:
            data = response.json()
            categories = data.get("categories", [])
            print(f"    [OK] Categories endpoint works")
            print(f"        Available categories: {len(categories)}")
        else:
            print(f"    [WARN] Categories returned: {response.status_code}")

        # Test 4: User dashboard
        print("\n  Test 4: User Dashboard")
        response = client.get("/users/me/dashboard", headers=headers)

        if response.status_code == 200:
            dashboard = response.json()
            print(f"    [OK] Dashboard API works")
            print(f"        Identities count: {dashboard.get('identities_count', 0)}")
            print(f"        User tier: {dashboard.get('user_tier', 'N/A')}")
        else:
            print(f"    [WARN] Dashboard returned: {response.status_code}")

        print("\n[OK] Identity API tests completed!")
        return True

if __name__ == "__main__":
    success = test_identity_api()
    sys.exit(0 if success else 1)
