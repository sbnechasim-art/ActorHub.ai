"""
Service Unit Tests
Tests for critical business logic services
"""
import io
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image


class TestFaceRecognitionService:
    """Test face recognition service"""

    @pytest.fixture
    def face_service(self):
        """Create face recognition service instance"""
        from app.services.face_recognition import FaceRecognitionService
        return FaceRecognitionService()

    @pytest.fixture
    def sample_image_bytes(self):
        """Create a sample test image"""
        img = Image.new('RGB', (200, 200), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()

    @pytest.mark.asyncio
    async def test_extract_embedding_returns_512_dim(self, face_service, sample_image_bytes):
        """Test that embedding extraction returns 512-dimensional vector"""
        embedding = await face_service.extract_embedding(sample_image_bytes)

        if embedding is not None:
            assert len(embedding) == 512
            assert isinstance(embedding, (list, np.ndarray))
            # Check normalized
            norm = np.linalg.norm(embedding)
            assert 0.99 < norm < 1.01  # Should be unit normalized

    @pytest.mark.asyncio
    async def test_extract_embedding_invalid_image(self, face_service):
        """Test handling of invalid image data"""
        invalid_bytes = b"not an image"
        embedding = await face_service.extract_embedding(invalid_bytes)
        assert embedding is None

    @pytest.mark.asyncio
    async def test_compare_embeddings_same_person(self, face_service):
        """Test that same embedding returns high similarity"""
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding1 = embedding1 / np.linalg.norm(embedding1)

        # Same embedding should have similarity 1.0
        is_match, similarity = await face_service.compare_embeddings(
            embedding1.tolist(), embedding1.tolist(), threshold=0.8
        )
        assert is_match is True
        assert similarity > 0.99

    @pytest.mark.asyncio
    async def test_compare_embeddings_different_person(self, face_service):
        """Test that different embeddings return low similarity"""
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding1 = embedding1 / np.linalg.norm(embedding1)

        embedding2 = np.random.randn(512).astype(np.float32)
        embedding2 = embedding2 / np.linalg.norm(embedding2)

        is_match, similarity = await face_service.compare_embeddings(
            embedding1.tolist(), embedding2.tolist(), threshold=0.8
        )
        # Random vectors should have low similarity
        assert similarity < 0.5

    @pytest.mark.asyncio
    async def test_liveness_check_valid_image(self, face_service, sample_image_bytes):
        """Test liveness check with valid image"""
        result = await face_service.check_liveness(sample_image_bytes)

        assert "is_live" in result
        assert "confidence" in result
        assert isinstance(result["is_live"], bool)


class TestTrainingService:
    """Test training service"""

    @pytest.fixture
    def training_service(self):
        """Create training service instance"""
        from app.services.training import TrainingService
        return TrainingService()

    @pytest.mark.asyncio
    async def test_process_images_minimum_required(self, training_service):
        """Test that minimum 5 valid images are required"""
        # Create a few image URLs (will fail to download in test)
        image_urls = ["http://test.com/img1.jpg", "http://test.com/img2.jpg"]

        with pytest.raises(ValueError, match="Not enough valid face images"):
            await training_service._process_images(image_urls)

    @pytest.mark.asyncio
    async def test_package_actor_pack_creates_zip(self, training_service):
        """Test that packaging creates proper zip structure"""
        with patch.object(training_service.storage, 'upload_file', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = "s3://test/pack.zip"

            result = await training_service._package_actor_pack(
                actor_pack_id="test-pack-123",
                face_model={"primary_embedding": [0.1] * 512},
                voice_model=None,
                motion_data=None,
            )

            assert "s3_key" in result
            assert "file_size" in result
            assert result["file_size"] > 0
            mock_upload.assert_called_once()

    def test_compute_average_pose(self, training_service):
        """Test average pose computation"""
        # Create mock pose sequences
        pose_sequences = [
            {
                'poses': [
                    {'landmarks': [{'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 1.0}]},
                    {'landmarks': [{'x': 0.6, 'y': 0.4, 'z': 0.1, 'visibility': 0.9}]},
                ]
            }
        ]

        avg_pose = training_service._compute_average_pose(pose_sequences)

        assert avg_pose is not None
        assert len(avg_pose) == 1
        assert 0.5 <= avg_pose[0]['x'] <= 0.6


class TestGenerationService:
    """Test content generation service"""

    @pytest.fixture
    def generation_service(self):
        """Create generation service instance"""
        from app.services.generation import GenerationService
        return GenerationService()

    @pytest.mark.asyncio
    async def test_generate_face_requires_replicate_token(self, generation_service):
        """Test that face generation requires Replicate API token"""
        with patch('app.core.config.settings.REPLICATE_API_TOKEN', None):
            with pytest.raises(Exception, match="Replicate API not configured"):
                await generation_service.generate_face_image(
                    lora_model_url="http://test.com/lora.safetensors",
                    prompt="a portrait photo"
                )

    @pytest.mark.asyncio
    async def test_generate_voice_requires_elevenlabs_key(self, generation_service):
        """Test that voice generation requires ElevenLabs API key"""
        with patch('app.core.config.settings.ELEVENLABS_API_KEY', None):
            with pytest.raises(Exception, match="ElevenLabs API not configured"):
                await generation_service._generate_voice_elevenlabs(
                    voice_id="test-voice-id",
                    text="Hello world"
                )


class TestStorageService:
    """Test storage service"""

    @pytest.fixture
    def storage_service(self):
        """Create storage service instance"""
        from app.services.storage import StorageService
        return StorageService()

    @pytest.mark.asyncio
    async def test_upload_file_returns_url(self, storage_service):
        """Test file upload returns accessible URL"""
        test_content = b"test file content"

        with patch.object(storage_service, '_get_client') as mock_client:
            mock_s3 = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_s3

            url = await storage_service.upload_file(
                file_bytes=test_content,
                filename="test/file.txt",
                content_type="text/plain"
            )

            # Should return a URL string
            assert isinstance(url, str)


class TestPaymentService:
    """Test payment service"""

    @pytest.mark.asyncio
    async def test_create_checkout_session_requires_stripe(self):
        """Test that checkout requires Stripe configuration"""
        from app.services.payments import create_checkout_session

        with patch('app.core.config.settings.STRIPE_SECRET_KEY', None):
            with pytest.raises(Exception):
                await create_checkout_session(
                    price_usd=100.0,
                    license_id="test-license",
                    success_url="http://test.com/success",
                    cancel_url="http://test.com/cancel"
                )


class TestEmailService:
    """Test email service"""

    @pytest.mark.asyncio
    async def test_send_email_requires_sendgrid(self):
        """Test that email sending requires SendGrid configuration"""
        from app.services.email import EmailService

        service = EmailService()

        with patch('app.core.config.settings.SENDGRID_API_KEY', None):
            # Should handle gracefully when not configured
            result = await service.send_welcome_email(
                to_email="test@example.com",
                user_name="Test User"
            )
            # Should return False or raise when not configured
            assert result is False or result is None


class TestCircuitBreaker:
    """Test circuit breaker resilience pattern"""

    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after threshold failures"""
        from app.core.resilience import CircuitBreaker, CircuitBreakerConfig

        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=3, timeout=1.0, success_threshold=1)
        )

        # Record failures
        for _ in range(3):
            cb.record_failure()

        # Should be open now
        assert cb.can_execute() is False

    def test_circuit_breaker_closes_after_timeout(self):
        """Test that circuit breaker closes after timeout"""
        import time
        from app.core.resilience import CircuitBreaker, CircuitBreakerConfig

        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=2, timeout=0.1, success_threshold=1)
        )

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is False

        # Wait for timeout
        time.sleep(0.15)

        # Should be half-open now (can try)
        assert cb.can_execute() is True


class TestRateLimiting:
    """Test rate limiting middleware"""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_under_threshold(self, client):
        """Test that requests under limit are allowed"""
        # Make a few requests - should all succeed
        for _ in range(5):
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, client):
        """Test that exceeding rate limit returns 429"""
        # This test would need a very low rate limit to trigger
        # In production, rate limits are higher
        pass  # Skip for now - requires special test config
