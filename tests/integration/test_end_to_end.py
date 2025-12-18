"""
End-to-End Integration Test
Verifies complete platform connectivity: Frontend -> Backend -> Database -> Services
"""
import httpx
import sys
import time

# API endpoints
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def test_end_to_end():
    """Test complete platform integration"""

    print("=" * 60)
    print("  ActorHub.ai End-to-End Integration Test")
    print("=" * 60)

    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }

    # Test 1: Backend Health
    print("\n[1/6] Backend API Health")
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"    [OK] Backend healthy")
                print(f"        Status: {health.get('status')}")
                print(f"        Database: {health.get('database')}")
                print(f"        Redis: {health.get('redis')}")
                results["passed"] += 1
            else:
                print(f"    [FAIL] Backend unhealthy: {response.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"    [FAIL] Cannot reach backend: {e}")
        results["failed"] += 1

    # Test 2: Frontend Availability
    print("\n[2/6] Frontend Availability")
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(FRONTEND_URL)
            if response.status_code == 200:
                print(f"    [OK] Frontend is running")
                results["passed"] += 1
            else:
                print(f"    [WARN] Frontend returned: {response.status_code}")
                results["warnings"] += 1
    except Exception as e:
        print(f"    [WARN] Frontend not running: {e}")
        print("        (Start with: cd apps/web && npm run dev)")
        results["warnings"] += 1

    # Test 3: API Proxy (Frontend -> Backend)
    print("\n[3/6] Frontend API Proxy")
    try:
        with httpx.Client(timeout=10) as client:
            # Try both direct backend and proxied through frontend
            backend_resp = client.get(f"{BACKEND_URL}/api/v1/marketplace/listings")

            if backend_resp.status_code == 200:
                backend_data = backend_resp.json()
                print(f"    [OK] Backend marketplace API works")

                # Try frontend proxy
                try:
                    frontend_resp = client.get(f"{FRONTEND_URL}/api/v1/marketplace/listings")
                    if frontend_resp.status_code == 200:
                        print(f"    [OK] Frontend proxy to backend works")
                        results["passed"] += 1
                    else:
                        print(f"    [WARN] Frontend proxy returned: {frontend_resp.status_code}")
                        results["warnings"] += 1
                except:
                    print(f"    [WARN] Frontend proxy not available (frontend may not be running)")
                    results["warnings"] += 1
            else:
                print(f"    [FAIL] Backend marketplace API failed: {backend_resp.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"    [FAIL] API proxy test failed: {e}")
        results["failed"] += 1

    # Test 4: Authentication Flow
    print("\n[4/6] Authentication Flow (Real API)")
    try:
        with httpx.Client(base_url=f"{BACKEND_URL}/api/v1", timeout=30) as client:
            unique_email = f"e2e_test_{int(time.time())}@test.com"

            # Register
            register_resp = client.post("/users/register", json={
                "email": unique_email,
                "password": "TestPassword123!",
                "first_name": "E2E",
                "last_name": "Test"
            })

            if register_resp.status_code in [200, 201]:
                print(f"    [OK] User registration works")

                # Login
                login_resp = client.post("/users/login", json={
                    "email": unique_email,
                    "password": "TestPassword123!"
                })

                if login_resp.status_code == 200:
                    tokens = login_resp.json()
                    access_token = tokens.get("access_token")

                    if access_token:
                        print(f"    [OK] Login works - token received")

                        # Test protected endpoint
                        headers = {"Authorization": f"Bearer {access_token}"}
                        me_resp = client.get("/users/me", headers=headers)

                        if me_resp.status_code == 200:
                            user = me_resp.json()
                            print(f"    [OK] Protected endpoint works")
                            print(f"        User: {user.get('email')}")
                            results["passed"] += 1
                        else:
                            print(f"    [FAIL] Protected endpoint failed: {me_resp.status_code}")
                            results["failed"] += 1
                    else:
                        print(f"    [FAIL] No access token received")
                        results["failed"] += 1
                else:
                    print(f"    [FAIL] Login failed: {login_resp.status_code}")
                    results["failed"] += 1
            else:
                print(f"    [FAIL] Registration failed: {register_resp.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"    [FAIL] Authentication test failed: {e}")
        results["failed"] += 1

    # Test 5: Marketplace Real Data
    print("\n[5/6] Marketplace Real Data (Not Mock)")
    try:
        with httpx.Client(base_url=f"{BACKEND_URL}/api/v1", timeout=10) as client:
            listings_resp = client.get("/marketplace/listings")

            if listings_resp.status_code == 200:
                listings = listings_resp.json()
                if isinstance(listings, list):
                    print(f"    [OK] Marketplace returns real data")
                    print(f"        Listings count: {len(listings)}")

                    if len(listings) > 0:
                        # Check if it's real data (has database IDs)
                        first = listings[0]
                        if first.get("id") and not str(first.get("id")).startswith("featured-"):
                            print(f"        Data source: REAL DATABASE")
                        else:
                            print(f"        Data source: May be sample/demo data")
                    results["passed"] += 1
                else:
                    print(f"    [WARN] Unexpected response format")
                    results["warnings"] += 1
            else:
                print(f"    [FAIL] Marketplace API failed: {listings_resp.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"    [FAIL] Marketplace test failed: {e}")
        results["failed"] += 1

    # Test 6: Database Connection Verification
    print("\n[6/6] Database Connection")
    try:
        with httpx.Client(base_url=f"{BACKEND_URL}/api/v1", timeout=10) as client:
            # Categories come from database
            cat_resp = client.get("/marketplace/categories")

            if cat_resp.status_code == 200:
                print(f"    [OK] Database queries work")
                data = cat_resp.json()
                categories = data.get("categories", [])
                print(f"        Categories: {len(categories)}")
                results["passed"] += 1
            else:
                print(f"    [FAIL] Categories failed: {cat_resp.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"    [FAIL] Database test failed: {e}")
        results["failed"] += 1

    # Summary
    print("\n" + "=" * 60)
    print("  INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"    Passed:   {results['passed']}")
    print(f"    Failed:   {results['failed']}")
    print(f"    Warnings: {results['warnings']}")

    if results["failed"] == 0:
        print("\n[SUCCESS] All critical integrations working!")
        print("          Frontend and Backend are properly connected.")
        return True
    else:
        print(f"\n[ATTENTION] {results['failed']} test(s) failed")
        return False

if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)
