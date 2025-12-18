"""
Authentication Flow Integration Test
Tests user registration, login, and token refresh
"""
import httpx
import sys
import time

API_URL = "http://localhost:8000/api/v1"

def test_auth_flow():
    """Test complete authentication flow"""

    print("Testing authentication flow...")

    with httpx.Client(base_url=API_URL, timeout=30) as client:

        # Test 1: Register new user
        print("\n  Test 1: User Registration")
        unique_email = f"integration_test_{int(time.time())}@test.com"
        register_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Integration",
            "last_name": "Test"
        }

        response = client.post("/users/register", json=register_data)

        if response.status_code == 200:
            print(f"    [OK] User registration successful: {unique_email}")
            user_data = response.json()
        elif response.status_code == 400 and "already registered" in response.text.lower():
            print("    [WARN] User already exists (OK for re-run)")
        else:
            print(f"    [FAIL] Registration failed: {response.status_code} - {response.text}")
            return False

        # Test 2: Login
        print("\n  Test 2: User Login")
        login_data = {
            "email": unique_email,
            "password": register_data["password"]
        }

        response = client.post("/users/login", json=login_data)

        if response.status_code == 200:
            print("    [OK] Login successful")
            tokens = response.json()
            access_token = tokens["access_token"]
            refresh_token = tokens.get("refresh_token")
            print(f"    [OK] Access token received (expires in {tokens.get('expires_in', 'N/A')}s)")
            if refresh_token:
                print("    [OK] Refresh token received")
        else:
            print(f"    [FAIL] Login failed: {response.status_code} - {response.text}")
            return False

        # Test 3: Access protected endpoint
        print("\n  Test 3: Protected Endpoint Access")
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/users/me", headers=headers)

        if response.status_code == 200:
            print("    [OK] Protected endpoint accessible")
            user_info = response.json()
            print(f"    [OK] User email: {user_info.get('email')}")
        else:
            print(f"    [FAIL] Protected endpoint failed: {response.status_code}")
            return False

        # Test 4: Token refresh
        if refresh_token:
            print("\n  Test 4: Token Refresh")
            response = client.post(
                "/users/refresh",
                params={"refresh_token": refresh_token}
            )

            if response.status_code == 200:
                print("    [OK] Token refresh successful")
                new_tokens = response.json()
                print("    [OK] New access token received")
            else:
                print(f"    [WARN] Token refresh failed: {response.status_code}")

        # Test 5: Invalid token
        print("\n  Test 5: Invalid Token Rejection")
        headers = {"Authorization": "Bearer invalid_token_here"}

        response = client.get("/users/me", headers=headers)

        if response.status_code == 401:
            print("    [OK] Invalid token correctly rejected")
        else:
            print(f"    [FAIL] Invalid token not rejected: {response.status_code}")
            return False

        print("\n[OK] All authentication tests passed!")
        return True

if __name__ == "__main__":
    success = test_auth_flow()
    sys.exit(0 if success else 1)
