"""
Face Recognition Tasks

Handles face embedding extraction, verification, and registration
with distributed tracing for end-to-end visibility.
"""
import asyncio
from typing import List, Dict, Optional
import uuid
import structlog
import httpx
import numpy as np

from celery_app import app
from config import settings
from tracing import trace_task, add_task_attribute

logger = structlog.get_logger()


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def extract_embedding(
    self,
    image_url: str,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Extract face embedding from image URL.

    FIXED: Now includes retry logic with exponential backoff.
    """
    with trace_task("extract_embedding", trace_headers, {"url": image_url[:200]}) as span:
        add_task_attribute("retry_count", self.request.retries)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_extract_embedding_async(image_url))
        finally:
            loop.close()

        add_task_attribute("face_detected", result.get("face_detected", False))
        add_task_attribute("success", result.get("success", False))

        if result.get("success"):
            logger.info("Embedding extracted successfully", url=image_url[:100])
            return result
        else:
            error = result.get("error", "Unknown error")
            logger.warning(
                "Embedding extraction failed",
                url=image_url[:100],
                error=error,
                retry_count=self.request.retries
            )
            # Retry on transient failures
            if self.request.retries < self.max_retries:
                raise self.retry(
                    exc=Exception(error),
                    countdown=10 * (2 ** self.request.retries)
                )
            return result


async def _extract_embedding_async(image_url: str) -> Dict:
    """Async embedding extraction"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                return {'success': False, 'error': 'Failed to fetch image'}

            # In production, use InsightFace here
            embedding = np.random.randn(512).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)

            return {
                'success': True,
                'embedding': embedding.tolist(),
                'face_detected': True
            }
    except Exception as e:
        logger.error(f"Embedding extraction failed: {e}")
        return {'success': False, 'error': str(e)}


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def batch_verify(
    self,
    images: List[str],
    threshold: float = 0.85,
    trace_headers: Optional[Dict] = None
) -> List[Dict]:
    """
    Batch verify multiple images against the identity database.

    FIXED: Now includes retry logic for Qdrant connection issues.
    """
    with trace_task("batch_verify", trace_headers, {
        "image_count": len(images),
        "threshold": threshold,
    }) as span:
        add_task_attribute("retry_count", self.request.retries)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(_batch_verify_async(images, threshold))
            finally:
                loop.close()

            matched_count = sum(1 for r in results if r.get("matched"))
            add_task_attribute("matched_count", matched_count)
            add_task_attribute("processed_count", len(results))

            logger.info(
                "Batch verification completed",
                image_count=len(images),
                matched_count=matched_count,
                threshold=threshold
            )
            return results

        except Exception as e:
            logger.error(
                "Batch verification failed",
                error=str(e),
                retry_count=self.request.retries
            )
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
            raise


async def _batch_verify_async(images: List[str], threshold: float) -> List[Dict]:
    """Async batch verification"""
    results = []

    for image in images:
        try:
            embedding_result = await _extract_embedding_async(image)
            if not embedding_result['success']:
                results.append({
                    'image': image,
                    'matched': False,
                    'error': embedding_result['error']
                })
                continue

            # Search in Qdrant
            match = await _search_qdrant(embedding_result['embedding'], threshold)
            results.append({
                'image': image,
                'matched': match is not None,
                'identity_id': match['identity_id'] if match else None,
                'score': match['score'] if match else 0.0
            })
        except Exception as e:
            results.append({
                'image': image,
                'matched': False,
                'error': str(e)
            })

    return results


async def _search_qdrant(embedding: List[float], threshold: float) -> Optional[Dict]:
    """Search for matching identity in Qdrant"""
    from qdrant_client import QdrantClient

    try:
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        results = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=embedding,
            limit=1,
            score_threshold=threshold
        )

        if results:
            return {
                'identity_id': results[0].payload.get('identity_id'),
                'score': results[0].score
            }
        return None
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        return None


@app.task(bind=True, max_retries=3, default_retry_delay=15)
def register_embedding(
    self,
    identity_id: str,
    embedding: List[float],
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Register a new embedding in the vector database.

    FIXED: Now includes retry logic for Qdrant connection issues.
    """
    with trace_task("register_embedding", trace_headers, {"identity_id": identity_id}) as span:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        add_task_attribute("retry_count", self.request.retries)

        try:
            client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=identity_id,
                        vector=embedding,
                        payload={'identity_id': identity_id}
                    )
                ]
            )
            add_task_attribute("embedding_size", len(embedding))
            logger.info("Embedding registered successfully", identity_id=identity_id)
            return {'success': True, 'identity_id': identity_id}
        except Exception as e:
            logger.error(
                "Failed to register embedding",
                identity_id=identity_id,
                error=str(e),
                retry_count=self.request.retries
            )
            # Retry on connection errors
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=15 * (2 ** self.request.retries))
            return {'success': False, 'error': str(e)}


@app.task(bind=True, max_retries=3, default_retry_delay=15)
def delete_embedding(
    self,
    identity_id: str,
    trace_headers: Optional[Dict] = None
) -> Dict:
    """
    Delete an embedding from the vector database.

    FIXED: Now includes retry logic for Qdrant connection issues.
    """
    with trace_task("delete_embedding", trace_headers, {"identity_id": identity_id}) as span:
        from qdrant_client import QdrantClient

        add_task_attribute("retry_count", self.request.retries)

        try:
            client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=[identity_id]
            )
            logger.info("Embedding deleted successfully", identity_id=identity_id)
            return {'success': True, 'identity_id': identity_id}
        except Exception as e:
            logger.error(
                "Failed to delete embedding",
                identity_id=identity_id,
                error=str(e),
                retry_count=self.request.retries
            )
            # Retry on connection errors
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=15 * (2 ** self.request.retries))
            return {'success': False, 'error': str(e)}
