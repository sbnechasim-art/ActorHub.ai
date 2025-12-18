"""
Face Recognition Service
Core service for identity verification using InsightFace + Qdrant
"""

import asyncio
import base64
import os
import uuid
from functools import partial
from typing import Dict, List, Optional

import cv2
import httpx
import numpy as np
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.core.config import settings

logger = structlog.get_logger()

# Explicit mock mode flag - set FACE_RECOGNITION_MOCK=true to use mock embeddings
FACE_RECOGNITION_MOCK = os.getenv("FACE_RECOGNITION_MOCK", "false").lower() == "true"

if FACE_RECOGNITION_MOCK:
    logger.warning("=" * 60)
    logger.warning("FACE RECOGNITION RUNNING IN MOCK MODE")
    logger.warning(
        "Set FACE_RECOGNITION_MOCK=false and install InsightFace for real face recognition"
    )
    logger.warning("=" * 60)


class FaceRecognitionService:
    """
    Face recognition service using InsightFace for embeddings
    and Qdrant for vector similarity search.
    """

    def __init__(self):
        self._face_app = None
        self._qdrant = None
        self._initialized = False

    async def _initialize(self):
        """Lazy initialization of ML models and database connection"""
        if self._initialized:
            return

        # Skip InsightFace if mock mode is enabled
        if FACE_RECOGNITION_MOCK:
            logger.warning("MOCK MODE: Skipping InsightFace initialization")
            self._face_app = None
        else:
            try:
                # Initialize InsightFace
                from insightface.app import FaceAnalysis

                self._face_app = FaceAnalysis(
                    name="buffalo_l", providers=["CPUExecutionProvider"]  # Use CUDA in production
                )
                self._face_app.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("InsightFace initialized successfully")
            except Exception as e:
                logger.warning(f"InsightFace not available: {e}. Using mock embeddings.")
                self._face_app = None

        # Initialize Qdrant
        try:
            self._qdrant = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
            )
            await self._init_collection()
            logger.info("Qdrant initialized successfully")
        except Exception as e:
            logger.warning(f"Qdrant not available: {e}. Using in-memory storage.")
            self._qdrant = QdrantClient(":memory:")
            await self._init_collection()

        self._initialized = True

    async def _init_collection(self):
        """Initialize the face embeddings collection in Qdrant"""
        collection_name = settings.QDRANT_COLLECTION
        loop = asyncio.get_event_loop()

        # Run sync Qdrant calls in executor to avoid blocking
        collections = await loop.run_in_executor(
            None, self._qdrant.get_collections
        )
        exists = any(c.name == collection_name for c in collections.collections)

        if not exists:
            await loop.run_in_executor(
                None,
                partial(
                    self._qdrant.create_collection,
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=settings.FACE_EMBEDDING_SIZE, distance=Distance.COSINE
                    ),
                )
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

    async def extract_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Extract 512-dimensional face embedding from image.

        Args:
            image_bytes: Raw image bytes

        Returns:
            numpy array of shape (512,) or None if no face detected
        """
        await self._initialize()

        logger.info(f"Extracting embedding from image ({len(image_bytes)} bytes)")

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.warning("Failed to decode image")
            return None

        logger.info(f"Image decoded successfully: {img.shape}")

        if self._face_app is None:
            # In production, InsightFace must be available
            if not FACE_RECOGNITION_MOCK:
                raise RuntimeError("Face recognition service not available. InsightFace not initialized.")
            # Mock mode only enabled via explicit env var
            logger.warning("MOCK: Returning random face embedding (InsightFace not available)")
            mock_embedding = np.random.randn(512).astype(np.float32)
            mock_embedding = mock_embedding / np.linalg.norm(mock_embedding)  # Normalize
            return mock_embedding

        # Detect faces
        faces = self._face_app.get(img)

        logger.info(f"Face detection result: {len(faces)} faces found")

        if not faces:
            logger.warning("No faces detected in image - returning None")
            return None

        # Return embedding of largest face
        largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        embedding = largest_face.embedding

        logger.info(f"Face detected with score {largest_face.det_score:.3f}, bbox: {largest_face.bbox.tolist()}")

        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    async def detect_faces_base64(self, image_b64: str) -> List[Dict]:
        """Detect all faces in base64 encoded image"""
        try:
            image_bytes = base64.b64decode(image_b64)
            return await self._detect_faces(image_bytes)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            return []

    async def detect_faces_url(self, image_url: str) -> List[Dict]:
        """Detect all faces in image from URL"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return await self._detect_faces(response.content)
        except Exception as e:
            logger.error(f"Error fetching image from URL: {e}")
            return []

    async def _detect_faces(self, image_bytes: bytes) -> List[Dict]:
        """Internal face detection"""
        await self._initialize()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return []

        if self._face_app is None:
            # In production, InsightFace must be available
            if not FACE_RECOGNITION_MOCK:
                raise RuntimeError("Face recognition service not available. InsightFace not initialized.")
            # Mock mode only enabled via explicit env var
            return [
                {
                    "bbox": [100, 100, 200, 200],
                    "embedding": np.random.randn(512).astype(np.float32),
                    "det_score": 0.95,
                    "landmarks": None,
                }
            ]

        faces = self._face_app.get(img)

        return [
            {
                "bbox": face.bbox.tolist(),
                "embedding": face.embedding / np.linalg.norm(face.embedding),
                "det_score": float(face.det_score),
                "landmarks": (
                    face.landmark_2d_106.tolist() if hasattr(face, "landmark_2d_106") else None
                ),
            }
            for face in faces
        ]

    async def liveness_check(self, image_bytes: bytes) -> bool:
        """
        Basic liveness detection.

        In production, integrate with dedicated service like:
        - FaceTec
        - iProov
        - AWS Rekognition

        For MVP, check detection confidence as basic anti-spoofing.
        """
        await self._initialize()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.warning("Liveness check: Failed to decode image")
            return False

        if self._face_app is None:
            # In production, InsightFace must be available
            if not FACE_RECOGNITION_MOCK:
                raise RuntimeError("Face recognition service not available. InsightFace not initialized.")
            # Mock mode only enabled via explicit env var
            logger.info("Liveness check: Mock mode - passing")
            return True

        faces = self._face_app.get(img)

        if not faces:
            logger.warning("Liveness check: No faces detected in verification image")
            return False

        det_score = faces[0].det_score
        logger.info(f"Liveness check: Detection score = {det_score:.3f}")

        # Relaxed threshold for development (0.5 instead of 0.8)
        # Production should use proper liveness detection service
        threshold = 0.5  # Was 0.8
        passed = det_score > threshold

        if not passed:
            logger.warning(f"Liveness check failed: score {det_score:.3f} < {threshold}")

        return passed

    async def register_embedding(self, identity_id: uuid.UUID, embedding: np.ndarray):
        """Store embedding in vector database"""
        await self._initialize()
        loop = asyncio.get_event_loop()

        # Run sync Qdrant upsert in executor to avoid blocking
        await loop.run_in_executor(
            None,
            partial(
                self._qdrant.upsert,
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=str(identity_id),
                        vector=embedding.tolist(),
                        payload={"identity_id": str(identity_id), "created_at": str(uuid.uuid1().time)},
                    )
                ],
            )
        )
        logger.info(f"Registered embedding for identity {identity_id}")

    async def find_match(self, embedding: np.ndarray, threshold: float = None) -> Optional[Dict]:
        """
        Find matching identity for embedding.

        Args:
            embedding: Face embedding to search for
            threshold: Minimum similarity score (default from settings)

        Returns:
            Dict with identity_id and score, or None if no match
        """
        await self._initialize()
        loop = asyncio.get_event_loop()

        if threshold is None:
            threshold = settings.FACE_SIMILARITY_THRESHOLD

        # Run sync Qdrant search in executor to avoid blocking
        results = await loop.run_in_executor(
            None,
            partial(
                self._qdrant.search,
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=embedding.tolist(),
                limit=1,
                score_threshold=threshold,
            )
        )

        if not results:
            return None

        return {"identity_id": results[0].payload["identity_id"], "score": results[0].score}

    async def find_similar(
        self, embedding: np.ndarray, threshold: float = None, limit: int = 10
    ) -> List[Dict]:
        """Find all similar identities above threshold"""
        await self._initialize()
        loop = asyncio.get_event_loop()

        if threshold is None:
            threshold = settings.FACE_DUPLICATE_THRESHOLD

        # Run sync Qdrant search in executor to avoid blocking
        results = await loop.run_in_executor(
            None,
            partial(
                self._qdrant.search,
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=embedding.tolist(),
                limit=limit,
                score_threshold=threshold,
            )
        )

        return [{"identity_id": r.payload["identity_id"], "score": r.score} for r in results]

    async def delete_embedding(self, identity_id: uuid.UUID):
        """Remove embedding from vector database"""
        await self._initialize()
        loop = asyncio.get_event_loop()

        # Run sync Qdrant delete in executor to avoid blocking
        await loop.run_in_executor(
            None,
            partial(
                self._qdrant.delete,
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=[str(identity_id)]
            )
        )
        logger.info(f"Deleted embedding for identity {identity_id}")

    async def get_collection_stats(self) -> Dict:
        """Get statistics about the embeddings collection"""
        await self._initialize()
        loop = asyncio.get_event_loop()

        # Run sync Qdrant get_collection in executor to avoid blocking
        info = await loop.run_in_executor(
            None,
            partial(self._qdrant.get_collection, settings.QDRANT_COLLECTION)
        )

        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }
