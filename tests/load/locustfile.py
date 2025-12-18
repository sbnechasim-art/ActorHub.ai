"""
ActorHub.ai Load Testing Suite
Tests system under 100+ concurrent users
"""
import random
import string
import base64
import time

from locust import HttpUser, task, between, events

# Test image (small placeholder)
TEST_IMAGE_B64 = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode()


class ActorHubUser(HttpUser):
    """Regular user browsing the site"""

    wait_time = between(1, 3)

    def on_start(self):
        """Login at session start"""
        self.email = f"loadtest_{random.randint(10000, 99999)}@test.com"
        self.password = "LoadTest123!"
        self.token = None

        # Try to register
        try:
            response = self.client.post("/api/v1/users/register", json={
                "email": self.email,
                "password": self.password,
                "full_name": "Load Test User"
            })
        except:
            pass

        # Login
        try:
            response = self.client.post(
                "/api/v1/users/login",
                data={
                    "username": self.email,
                    "password": self.password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                self.token = response.json().get("access_token")
        except:
            pass

    @property
    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ===== Public Endpoints =====

    @task(10)
    def view_home(self):
        """View home page"""
        self.client.get("/")

    @task(8)
    def view_marketplace(self):
        """View Marketplace"""
        self.client.get("/api/v1/marketplace/listings")

    @task(5)
    def view_categories(self):
        """View categories"""
        self.client.get("/api/v1/marketplace/categories")

    @task(3)
    def search_marketplace(self):
        """Search Marketplace"""
        queries = ["model", "actor", "celebrity", "influencer"]
        self.client.get(f"/api/v1/marketplace/listings?search={random.choice(queries)}")

    @task(2)
    def health_check(self):
        """Health check"""
        self.client.get("/health")

    # ===== Authenticated Endpoints =====

    @task(5)
    def view_my_identities(self):
        """View my identities"""
        if self.token:
            self.client.get("/api/v1/identity/mine", headers=self.auth_headers)

    @task(3)
    def view_profile(self):
        """View profile"""
        if self.token:
            self.client.get("/api/v1/users/me", headers=self.auth_headers)


class APIUser(HttpUser):
    """API user (simulating Sora/Kling)"""

    wait_time = between(0.5, 2)
    weight = 2  # More API users

    def on_start(self):
        """Get API Key"""
        self.api_key = "test_api_key"

    @task(10)
    def verify_face_api(self):
        """Fast Verify API calls"""
        self.client.post(
            "/api/v1/identity/verify",
            json={"image_base64": TEST_IMAGE_B64},
            headers={"X-API-Key": self.api_key}
        )

    @task(5)
    def get_marketplace_listings(self):
        """Get marketplace listings"""
        self.client.get("/api/v1/marketplace/listings")


# ===== Event Handlers =====

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("="*60)
    print("Starting ActorHub.ai Load Test")
    print("="*60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("="*60)
    print("Load Test Complete")
    print("="*60)
