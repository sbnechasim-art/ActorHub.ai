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
        """Test successful login"""
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
