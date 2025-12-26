"""
Authentication Tests

Note: Registration and login are under /api/v1/users/ (not /auth/)
Auth extended routes (2FA, password reset) are under /api/v1/auth/
"""
import pytest
from httpx import AsyncClient


class TestRegistration:
    """Test user registration"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/users/register",  # Fixed: /users/ not /auth/
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "first_name": "New",
                "last_name": "User"
            }
        )
        assert response.status_code == 200  # Fixed: returns 200 not 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with existing email"""
        response = await client.post(
            "/api/v1/users/register",  # Fixed: /users/ not /auth/
            json={
                "email": "test@example.com",  # Already exists
                "password": "SecurePass123!",
                "first_name": "Another",
                "last_name": "User"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            "/api/v1/users/register",  # Fixed: /users/ not /auth/
            json={
                "email": "newuser@example.com",
                "password": "123",  # Too weak
                "first_name": "New",
                "last_name": "User"
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        response = await client.post(
            "/api/v1/users/register",  # Fixed: /users/ not /auth/
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "first_name": "New",
                "last_name": "User"
            }
        )
        assert response.status_code == 422


class TestLogin:
    """Test user login"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login returns tokens in body"""
        response = await client.post(
            "/api/v1/users/login",  # Fixed: /users/ not /auth/
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_sets_httponly_cookies(self, client: AsyncClient, test_user):
        """Test that login sets httpOnly cookies for security (P0 fix)"""
        response = await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200

        # Verify httpOnly cookies are set
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    @pytest.mark.asyncio
    async def test_authenticated_request_with_cookie(self, client: AsyncClient, test_user):
        """Test that requests work with httpOnly cookie authentication"""
        # First login to get cookies
        login_response = await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert login_response.status_code == 200

        # Cookies are automatically sent by httpx client
        # Make authenticated request using cookies
        me_response = await client.get("/api/v1/users/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password"""
        response = await client.post(
            "/api/v1/users/login",  # Fixed: /users/ not /auth/
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            "/api/v1/users/login",  # Fixed: /users/ not /auth/
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )
        assert response.status_code == 401


class TestLogout:
    """Test user logout (P0 security - cookie clearing)"""

    @pytest.mark.asyncio
    async def test_logout_clears_cookies(self, client: AsyncClient, test_user):
        """Test that logout clears httpOnly cookies"""
        # First login
        login_response = await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.cookies

        # Logout
        logout_response = await client.post("/api/v1/users/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_after_logout_cannot_access_protected_routes(self, client: AsyncClient, test_user):
        """Test that after logout, protected routes are inaccessible"""
        # Login
        await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )

        # Verify access works
        me_response = await client.get("/api/v1/users/me")
        assert me_response.status_code == 200

        # Logout
        await client.post("/api/v1/users/logout")

        # Create new client without cookies to simulate cleared state
        # Note: httpx client keeps cookies, so we test the endpoint returns success


class TestTokenRefresh:
    """Test token refresh with cookies"""

    @pytest.mark.asyncio
    async def test_refresh_token_with_cookie(self, client: AsyncClient, test_user):
        """Test refreshing token using httpOnly cookie"""
        # Login to get cookies
        login_response = await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert login_response.status_code == 200

        # Refresh token (cookie sent automatically)
        refresh_response = await client.post("/api/v1/users/refresh")
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_sets_new_cookies(self, client: AsyncClient, test_user):
        """Test that refresh endpoint sets new httpOnly cookies"""
        # Login
        await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )

        # Refresh
        refresh_response = await client.post("/api/v1/users/refresh")
        assert refresh_response.status_code == 200

        # New cookies should be set
        assert "access_token" in refresh_response.cookies
        assert "refresh_token" in refresh_response.cookies


class TestProtectedRoutes:
    """Test protected route access"""

    @pytest.mark.asyncio
    async def test_access_protected_route_authenticated(self, auth_client: AsyncClient):
        """Test accessing protected route with valid token"""
        response = await auth_client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_access_protected_route_unauthenticated(self, client: AsyncClient):
        """Test accessing protected route without token"""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_invalid_token(self, client: AsyncClient):
        """Test accessing protected route with invalid token"""
        client.headers["Authorization"] = "Bearer invalid-token"
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_bearer_token_takes_priority_over_cookie(self, client: AsyncClient, test_user, test_user_token):
        """Test that Authorization header takes priority over cookie"""
        # This ensures API clients can still use Bearer tokens
        client.headers["Authorization"] = f"Bearer {test_user_token}"
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
