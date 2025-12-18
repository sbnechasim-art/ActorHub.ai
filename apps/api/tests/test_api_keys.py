"""
API Keys Tests
"""
import pytest
from httpx import AsyncClient


class TestApiKeyManagement:
    """Test API key management endpoints"""

    @pytest.mark.asyncio
    async def test_create_api_key_authenticated(self, auth_client: AsyncClient):
        """Test creating an API key when authenticated"""
        response = await auth_client.post(
            "/api/v1/users/api-keys",
            json={
                "name": "Test API Key",
                "permissions": ["identity:read", "identity:verify"],
                "rate_limit": 1000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("ah_")
        assert "key_info" in data
        assert data["key_info"]["name"] == "Test API Key"

    @pytest.mark.asyncio
    async def test_create_api_key_unauthenticated(self, client: AsyncClient):
        """Test creating an API key without authentication"""
        response = await client.post(
            "/api/v1/users/api-keys",
            json={"name": "Unauthorized Key"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_api_keys(self, auth_client: AsyncClient):
        """Test listing API keys"""
        # First create a key
        await auth_client.post(
            "/api/v1/users/api-keys",
            json={"name": "List Test Key"},
        )

        # Then list keys
        response = await auth_client.get("/api/v1/users/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_api_key_expiration(self, auth_client: AsyncClient):
        """Test creating an API key with expiration"""
        response = await auth_client.post(
            "/api/v1/users/api-keys",
            json={
                "name": "Expiring Key",
                "expires_in_days": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key_info"]["expires_at"] is not None


class TestTokenRefresh:
    """Test token refresh functionality"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test refreshing access token"""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/users/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        refresh_token = tokens.get("refresh_token")

        if refresh_token:
            # Use refresh token to get new access token
            refresh_response = await client.post(
                "/api/v1/users/refresh",
                params={"refresh_token": refresh_token},
            )
            assert refresh_response.status_code == 200
            new_tokens = refresh_response.json()
            assert "access_token" in new_tokens
            assert "refresh_token" in new_tokens

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refreshing with invalid token"""
        response = await client.post(
            "/api/v1/users/refresh",
            params={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
