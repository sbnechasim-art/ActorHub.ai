"""
E2E Tests for Actor Registration Flow
Tests the complete flow: Register -> Create Identity -> Upload Photos -> Start Training
"""

import pytest
from httpx import AsyncClient
import base64
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np


class TestActorRegistrationFlow:
    """
    Full flow: Register -> Create Identity -> Upload Photos -> Start Training
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_actor_registration(self, client: AsyncClient):
        """Test complete actor registration flow"""

        # Step 1: Register new user
        register_response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "actor@test-flow.com",
                "password": "SecurePass123!",
                "first_name": "Test",
                "last_name": "Actor"
            }
        )
        assert register_response.status_code == 200
        user_data = register_response.json()
        assert user_data["email"] == "actor@test-flow.com"
        user_id = user_data["id"]

        # Step 2: Login to get token
        login_response = await client.post(
            "/api/v1/users/login",
            json={
                "email": "actor@test-flow.com",
                "password": "SecurePass123!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Create Identity
        identity_response = await client.post(
            "/api/v1/identity",
            headers=auth_headers,
            json={
                "display_name": "Test Actor",
                "category": "actor",
                "bio": "I am a test actor for E2E testing"
            }
        )
        assert identity_response.status_code == 201
        identity_data = identity_response.json()
        identity_id = identity_data["id"]
        assert identity_data["display_name"] == "Test Actor"

        # Step 4: Upload training images (minimum 8)
        with patch('app.services.face_recognition.FaceRecognitionService') as mock_face:
            mock_face_instance = MagicMock()
            mock_face_instance.extract_embedding = AsyncMock(
                return_value=np.random.rand(512).tolist()
            )
            mock_face.return_value = mock_face_instance

            for i in range(8):
                # Create fake image bytes
                fake_image = base64.b64encode(
                    np.zeros((224, 224, 3), dtype=np.uint8).tobytes()
                ).decode()

                upload_response = await client.post(
                    f"/api/v1/identity/{identity_id}/upload",
                    headers=auth_headers,
                    files={
                        "file": (
                            f"photo{i}.jpg",
                            base64.b64decode(fake_image),
                            "image/jpeg"
                        )
                    }
                )
                assert upload_response.status_code == 200

        # Step 5: Verify images were uploaded
        identity_detail = await client.get(
            f"/api/v1/identity/{identity_id}",
            headers=auth_headers
        )
        assert identity_detail.status_code == 200
        detail_data = identity_detail.json()
        assert detail_data.get("images_count", 0) >= 8 or "actor_pack" in detail_data

        # Step 6: Start training
        with patch('app.services.training.TrainingService') as mock_training:
            mock_training_instance = MagicMock()
            mock_training_instance.start_training = AsyncMock()
            mock_training.return_value = mock_training_instance

            training_response = await client.post(
                f"/api/v1/identity/{identity_id}/train",
                headers=auth_headers
            )
            # Should be 202 Accepted or 200
            assert training_response.status_code in [200, 202]

        # Step 7: Verify identity status
        final_status = await client.get(
            f"/api/v1/identity/{identity_id}",
            headers=auth_headers
        )
        assert final_status.status_code == 200
        final_data = final_status.json()
        # Should be pending or processing
        if "actor_pack" in final_data and final_data["actor_pack"]:
            assert final_data["actor_pack"]["training_status"] in [
                "PENDING", "PROCESSING", "COMPLETED"
            ]


class TestActorRegistrationValidation:
    """Test validation throughout the registration flow"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_registration_flow_weak_password(self, client: AsyncClient):
        """Test flow fails with weak password"""
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "weak@test.com",
                "password": "123",  # Too weak
                "first_name": "Test",
                "last_name": "User"
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_registration_flow_duplicate_email(
        self, client: AsyncClient, test_user
    ):
        """Test flow fails with duplicate email"""
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "test@example.com",  # Already exists
                "password": "SecurePass123!",
                "first_name": "Another",
                "last_name": "User"
            }
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_training_requires_minimum_images(self, auth_client: AsyncClient):
        """Test training fails without minimum images"""
        # Create identity
        identity_response = await auth_client.post(
            "/api/v1/identity",
            json={
                "display_name": "No Images Actor",
                "category": "actor"
            }
        )
        assert identity_response.status_code == 201
        identity_id = identity_response.json()["id"]

        # Try to start training without uploading images
        training_response = await auth_client.post(
            f"/api/v1/identity/{identity_id}/train"
        )
        # Should fail due to insufficient images
        assert training_response.status_code in [400, 422]


class TestIdentityProtection:
    """Test identity protection verification"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_verify_unregistered_face(self, auth_client: AsyncClient):
        """Test verification of unregistered face returns not protected"""
        fake_image = base64.b64encode(
            np.zeros((224, 224, 3), dtype=np.uint8).tobytes()
        ).decode()

        with patch('app.services.face_recognition.FaceRecognitionService') as mock_face:
            mock_face_instance = MagicMock()
            mock_face_instance.extract_embedding = AsyncMock(
                return_value=np.random.rand(512).tolist()
            )
            mock_face_instance.find_match = AsyncMock(return_value=None)
            mock_face.return_value = mock_face_instance

            response = await auth_client.post(
                "/api/v1/identity/verify",
                json={
                    "image_base64": fake_image
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("protected") is False or data.get("match") is None

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_verify_registered_face_returns_protected(
        self, auth_client: AsyncClient, test_identity_with_embedding
    ):
        """Test verification of registered face returns protected"""
        from uuid import uuid4

        fake_image = base64.b64encode(
            np.zeros((224, 224, 3), dtype=np.uint8).tobytes()
        ).decode()

        with patch('app.services.face_recognition.FaceRecognitionService') as mock_face:
            mock_face_instance = MagicMock()
            mock_face_instance.extract_embedding = AsyncMock(
                return_value=np.random.rand(512).tolist()
            )
            mock_face_instance.find_match = AsyncMock(return_value={
                "identity_id": str(test_identity_with_embedding.id),
                "score": 0.95
            })
            mock_face.return_value = mock_face_instance

            response = await auth_client.post(
                "/api/v1/identity/verify",
                json={
                    "image_base64": fake_image
                }
            )

            assert response.status_code == 200
            data = response.json()
            # Should indicate protected or have a match
            assert data.get("protected") is True or data.get("match") is not None
