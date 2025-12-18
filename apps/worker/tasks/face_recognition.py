"""
Face Recognition Tasks
"""
import asyncio
from typing import List, Dict, Optional
import uuid
import structlog
import httpx
import numpy as np

from celery_app import app
from config import settings

logger = structlog.get_logger()


@app.task(bind=True)
def extract_embedding(self, image_url: str) -> Dict:
    """
    Extract face embedding from image URL.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_extract_embedding_async(image_url))


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


@app.task(bind=True)
def batch_verify(self, images: List[str], threshold: float = 0.85) -> List[Dict]:
    """
    Batch verify multiple images against the identity database.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_batch_verify_async(images, threshold))


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


@app.task
def register_embedding(identity_id: str, embedding: List[float]) -> Dict:
    """
    Register a new embedding in the vector database.
    """
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

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
        return {'success': True, 'identity_id': identity_id}
    except Exception as e:
        logger.error(f"Failed to register embedding: {e}")
        return {'success': False, 'error': str(e)}


@app.task
def delete_embedding(identity_id: str) -> Dict:
    """
    Delete an embedding from the vector database.
    """
    from qdrant_client import QdrantClient

    try:
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=[identity_id]
        )
        return {'success': True, 'identity_id': identity_id}
    except Exception as e:
        logger.error(f"Failed to delete embedding: {e}")
        return {'success': False, 'error': str(e)}
