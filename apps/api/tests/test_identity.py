"""
Identity API Tests
"""
import pytest
import base64
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestIdentityRegistration:
    """Test identity registration"""

    @pytest.mark.asyncio
    async def test_register_identity_success(self, auth_client: AsyncClient):
        """Test successful identity registration"""
        # Create a small test image (1x1 pixel PNG)
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        with patch('app.services.face_recognition.FaceRecognitionService.extract_embedding') as mock_extract:
            mock_extract.return_value = [0.1] * 512  # Mock embedding

            response = await auth_client.post(
                "/api/v1/identity/register",
                files={
                    "face_image": ("face.png", test_image, "image/png"),
                    "verification_image": ("verify.png", test_image, "image/png")
                },
                data={
                    "display_name": "Test Identity",
                    "protection_level": "free"
                }
            )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["display_name"] == "Test Identity"

    @pytest.mark.asyncio
    async def test_register_identity_unauthenticated(self, client: AsyncClient):
        """Test identity registration without authentication"""
        response = await client.post(
            "/api/v1/identity/register",
            data={"display_name": "Test"}
        )
        assert response.status_code == 401


class TestIdentityVerification:
    """Test identity verification API"""

    @pytest.mark.asyncio
    async def test_verify_with_api_key(self, client: AsyncClient, db_session):
        """Test verification with API key"""
        # This would need an API key fixture
        pass

    @pytest.mark.asyncio
    async def test_verify_no_match(self, auth_client: AsyncClient):
        """Test verification with no matching identity"""
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        with patch('app.services.face_recognition.FaceRecognitionService.extract_embedding') as mock_extract:
            mock_extract.return_value = [0.1] * 512
            with patch('app.services.face_recognition.FaceRecognitionService.find_match') as mock_find:
                mock_find.return_value = None

                response = await auth_client.post(
                    "/api/v1/identity/verify",
                    json={
                        "image": base64.b64encode(test_image).decode()
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False


class TestIdentityManagement:
    """Test identity management endpoints"""

    @pytest.mark.asyncio
    async def test_get_my_identities(self, auth_client: AsyncClient):
        """Test getting user's identities"""
        response = await auth_client.get("/api/v1/identity/mine")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_identity_stats(self, auth_client: AsyncClient):
        """Test getting identity statistics"""
        response = await auth_client.get("/api/v1/identity/stats")
        assert response.status_code == 200
