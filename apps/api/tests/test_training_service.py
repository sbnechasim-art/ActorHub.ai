"""
Tests for Training Service
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.training import TrainingService


class TestTrainingService:
    """Test training service functionality"""

    @pytest.fixture
    def training_service(self):
        """Create training service instance"""
        return TrainingService()

    @pytest.mark.asyncio
    async def test_train_face_model(self, training_service):
        """Test face model training with embeddings"""
        # Create fake embeddings (512-dim vectors)
        embeddings = [np.random.rand(512).tolist() for _ in range(5)]

        face_data = {
            "embeddings": embeddings,
            "images": [b"fake_image"] * 5,
            "count": 5,
        }

        result = await training_service._train_face_model(face_data)

        assert result is not None
        assert "primary_embedding" in result
        assert "embeddings_count" in result
        assert result["embeddings_count"] == 5
        assert len(result["primary_embedding"]) == 512

    @pytest.mark.asyncio
    async def test_assess_quality_with_embeddings(self, training_service):
        """Test quality assessment with real embeddings"""
        import os
        os.environ["QUALITY_ASSESSMENT_MOCK"] = "false"

        # Create similar embeddings (high consistency)
        base = np.random.rand(512)
        embeddings = [
            (base + np.random.rand(512) * 0.1).tolist()  # Small variation
            for _ in range(10)
        ]

        face_data = {"embeddings": embeddings}
        pack_result = {"voice": False}

        result = await training_service._assess_quality(pack_result, face_data)

        assert "overall" in result
        assert "authenticity" in result
        assert "consistency" in result
        # High consistency expected for similar embeddings
        assert result["consistency"] > 50.0

    @pytest.mark.asyncio
    async def test_assess_quality_mock_mode(self, training_service):
        """Test quality assessment in mock mode"""
        import os
        os.environ["QUALITY_ASSESSMENT_MOCK"] = "true"

        pack_result = {"voice": True}

        result = await training_service._assess_quality(pack_result)

        # Should return fixed mock values
        assert result["overall"] == 85.0
        assert result["authenticity"] == 88.0
        assert result["consistency"] == 82.0
        assert result["voice"] == 80.0

    @pytest.mark.asyncio
    async def test_extract_motion_no_videos(self, training_service):
        """Test motion extraction with no videos"""
        result = await training_service._extract_motion([])
        assert result is None

    @pytest.mark.asyncio
    async def test_compute_average_pose(self, training_service):
        """Test average pose computation"""
        # Create fake pose sequences
        pose_sequences = [
            {
                "poses": [
                    {
                        "landmarks": [
                            {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}
                            for _ in range(33)  # 33 MediaPipe pose landmarks
                        ]
                    }
                    for _ in range(5)  # 5 frames
                ]
            }
        ]

        result = training_service._compute_average_pose(pose_sequences)

        assert result is not None
        assert len(result) == 33
        assert result[0]["x"] == 0.5
        assert result[0]["visibility"] == 1.0

    @pytest.mark.asyncio
    async def test_compute_average_pose_empty(self, training_service):
        """Test average pose with empty input"""
        result = training_service._compute_average_pose([])
        assert result is None


class TestLoRATraining:
    """Test LoRA training functionality"""

    @pytest.fixture
    def training_service(self):
        return TrainingService()

    @pytest.mark.asyncio
    async def test_lora_training_no_token(self, training_service):
        """Test LoRA training fails gracefully without token"""
        import os
        original = os.environ.get("REPLICATE_API_TOKEN")
        os.environ["REPLICATE_API_TOKEN"] = ""

        result = await training_service._train_lora_replicate(
            [b"image1", b"image2"],
            "test_identity"
        )

        assert result is None

        if original:
            os.environ["REPLICATE_API_TOKEN"] = original

    @pytest.mark.asyncio
    async def test_lora_training_no_package(self, training_service):
        """Test LoRA training handles missing package"""
        with patch.dict("sys.modules", {"replicate": None}):
            result = await training_service._train_lora_replicate(
                [b"image1", b"image2"],
                "test_identity"
            )
            # Should return None gracefully
            assert result is None


class TestVoiceTraining:
    """Test voice training functionality"""

    @pytest.fixture
    def training_service(self):
        return TrainingService()

    @pytest.mark.asyncio
    async def test_voice_training_no_audio(self, training_service):
        """Test voice training with no audio returns None"""
        result = await training_service._train_voice_model([])
        assert result is None

    @pytest.mark.asyncio
    async def test_voice_training_no_api_key(self, training_service):
        """Test voice training falls back without API key"""
        import os
        original = os.environ.get("ELEVENLABS_API_KEY")
        os.environ["ELEVENLABS_API_KEY"] = ""

        result = await training_service._train_voice_model(
            ["https://example.com/audio.mp3"]
        )

        # Should return fallback config - reference_only mode stores audio for later use
        assert result is not None
        assert result["provider"] == "reference_only"
        assert "stored_audio_keys" in result or "audio_count" in result

        if original:
            os.environ["ELEVENLABS_API_KEY"] = original


class TestPackaging:
    """Test actor pack packaging"""

    @pytest.fixture
    def training_service(self):
        return TrainingService()

    @pytest.mark.asyncio
    async def test_package_actor_pack(self, training_service):
        """Test packaging actor pack"""
        with patch.object(
            training_service.storage, "upload_file"
        ) as mock_upload:
            mock_upload.return_value = None

            result = await training_service._package_actor_pack(
                actor_pack_id="test-pack-123",
                face_model={"primary_embedding": [0.1] * 512},
                voice_model={"provider": "elevenlabs", "voice_id": "abc123"},
                motion_data={"status": "completed"},
            )

            assert result is not None
            assert "s3_key" in result
            assert "file_size" in result
            assert result["file_size"] > 0

            # Verify upload was called
            mock_upload.assert_called_once()
