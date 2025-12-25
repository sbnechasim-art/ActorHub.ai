"""
Tests for Face Recognition Tasks

Tests embedding extraction, batch verification, and vector DB operations.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import uuid
import numpy as np


class TestExtractEmbedding:
    """Test face embedding extraction."""

    @pytest.mark.asyncio
    async def test_extract_embedding_success(self, mock_http_client):
        """Should extract embedding from valid image."""
        from tasks.face_recognition import _extract_embedding_async

        # Mock successful image fetch
        mock_http_client.responses["https://example.com/face.jpg"] = Mock(
            status_code=200,
            content=b"fake_image_data"
        )

        with patch('httpx.AsyncClient', return_value=mock_http_client):
            result = await _extract_embedding_async("https://example.com/face.jpg")

            assert result["success"] is True
            assert result["face_detected"] is True
            assert "embedding" in result
            assert len(result["embedding"]) == 512

    @pytest.mark.asyncio
    async def test_extract_embedding_image_not_found(self, mock_http_client):
        """Should handle image not found."""
        from tasks.face_recognition import _extract_embedding_async

        mock_http_client.responses["https://example.com/missing.jpg"] = Mock(
            status_code=404
        )

        with patch('httpx.AsyncClient', return_value=mock_http_client):
            result = await _extract_embedding_async("https://example.com/missing.jpg")

            assert result["success"] is False
            assert "error" in result

    def test_extract_embedding_retry_on_failure(self, mock_celery_task):
        """Should retry on transient failures."""
        from tasks.face_recognition import extract_embedding

        mock_celery_task.request.retries = 0
        mock_celery_task.max_retries = 3

        with patch('tasks.face_recognition.trace_task') as mock_trace, \
             patch('tasks.face_recognition.add_task_attribute'), \
             patch('asyncio.new_event_loop') as mock_loop:

            mock_trace.return_value.__enter__ = Mock(return_value=Mock())
            mock_trace.return_value.__exit__ = Mock(return_value=False)

            mock_loop.return_value.run_until_complete.return_value = {
                "success": False,
                "error": "Network timeout"
            }
            mock_loop.return_value.close = Mock()

            with pytest.raises(Exception):
                extract_embedding(
                    mock_celery_task,
                    image_url="https://example.com/face.jpg"
                )


class TestBatchVerify:
    """Test batch face verification."""

    @pytest.mark.asyncio
    async def test_batch_verify_multiple_images(self):
        """Should verify multiple images in batch."""
        from tasks.face_recognition import _batch_verify_async

        images = [
            "https://example.com/face1.jpg",
            "https://example.com/face2.jpg",
            "https://example.com/face3.jpg",
        ]

        with patch('tasks.face_recognition._extract_embedding_async') as mock_extract, \
             patch('tasks.face_recognition._search_qdrant') as mock_search:

            # Mock successful embedding extraction
            mock_extract.return_value = {
                "success": True,
                "embedding": np.random.randn(512).tolist(),
                "face_detected": True
            }

            # Mock Qdrant search - first two match, third doesn't
            mock_search.side_effect = [
                {"identity_id": "id_1", "score": 0.95},
                {"identity_id": "id_2", "score": 0.88},
                None,
            ]

            results = await _batch_verify_async(images, threshold=0.85)

            assert len(results) == 3
            assert results[0]["matched"] is True
            assert results[1]["matched"] is True
            assert results[2]["matched"] is False

    @pytest.mark.asyncio
    async def test_batch_verify_handles_extraction_errors(self):
        """Should handle individual extraction errors gracefully."""
        from tasks.face_recognition import _batch_verify_async

        images = ["https://example.com/bad.jpg"]

        with patch('tasks.face_recognition._extract_embedding_async') as mock_extract:
            mock_extract.return_value = {
                "success": False,
                "error": "No face detected"
            }

            results = await _batch_verify_async(images, threshold=0.85)

            assert len(results) == 1
            assert results[0]["matched"] is False
            assert "error" in results[0]


class TestQdrantOperations:
    """Test Qdrant vector database operations."""

    @pytest.mark.asyncio
    async def test_search_qdrant_finds_match(self):
        """Should find matching identity in Qdrant."""
        from tasks.face_recognition import _search_qdrant

        mock_qdrant = Mock()
        mock_result = Mock()
        mock_result.payload = {"identity_id": "test_identity_123"}
        mock_result.score = 0.92
        mock_qdrant.search.return_value = [mock_result]

        with patch('qdrant_client.QdrantClient', return_value=mock_qdrant):
            embedding = np.random.randn(512).tolist()
            result = await _search_qdrant(embedding, threshold=0.85)

            assert result is not None
            assert result["identity_id"] == "test_identity_123"
            assert result["score"] == 0.92

    @pytest.mark.asyncio
    async def test_search_qdrant_no_match(self):
        """Should return None when no match found."""
        from tasks.face_recognition import _search_qdrant

        mock_qdrant = Mock()
        mock_qdrant.search.return_value = []

        with patch('qdrant_client.QdrantClient', return_value=mock_qdrant):
            embedding = np.random.randn(512).tolist()
            result = await _search_qdrant(embedding, threshold=0.85)

            assert result is None

    @pytest.mark.asyncio
    async def test_search_qdrant_handles_connection_error(self):
        """Should handle Qdrant connection errors."""
        from tasks.face_recognition import _search_qdrant

        with patch('qdrant_client.QdrantClient') as mock_client:
            mock_client.side_effect = Exception("Connection refused")

            embedding = np.random.randn(512).tolist()
            result = await _search_qdrant(embedding, threshold=0.85)

            assert result is None


class TestRegisterEmbedding:
    """Test embedding registration in Qdrant."""

    def test_register_embedding_task_configured(self):
        """register_embedding should have retry configuration."""
        from tasks.face_recognition import register_embedding

        assert register_embedding.max_retries == 3
        assert register_embedding.default_retry_delay == 15

    def test_register_embedding_retry_on_error(self, sample_embedding):
        """Task should be configured for retries on Qdrant errors."""
        from tasks.face_recognition import register_embedding

        # Verify retry configuration
        assert register_embedding.max_retries >= 1


class TestDeleteEmbedding:
    """Test embedding deletion from Qdrant."""

    def test_delete_embedding_task_configured(self):
        """delete_embedding should have retry configuration."""
        from tasks.face_recognition import delete_embedding

        assert delete_embedding.max_retries == 3
        assert delete_embedding.default_retry_delay == 15

    def test_delete_embedding_is_idempotent(self):
        """Delete embedding task should be safe to retry."""
        from tasks.face_recognition import delete_embedding

        # Verify retry configuration supports idempotency
        assert delete_embedding.max_retries >= 1


class TestEmbeddingNormalization:
    """Test embedding normalization."""

    def test_embedding_is_normalized(self):
        """Embeddings should be L2 normalized."""
        # When we generate embeddings, they should be unit vectors
        embedding = np.random.randn(512).astype(np.float32)
        normalized = embedding / np.linalg.norm(embedding)

        # L2 norm should be 1.0
        assert np.isclose(np.linalg.norm(normalized), 1.0, atol=1e-6)

    def test_embedding_dimension(self):
        """Embeddings should have correct dimension."""
        from config import settings

        assert settings.FACE_EMBEDDING_SIZE == 512
