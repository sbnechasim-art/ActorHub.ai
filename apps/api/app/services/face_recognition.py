"""
Face Recognition Service
Core service for identity verification using InsightFace + Qdrant
"""

# Load .env file early before any os.getenv calls
from dotenv import load_dotenv
load_dotenv()

import asyncio
import base64
import ipaddress
import os
import uuid
from functools import partial
from typing import Dict, List, Optional
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointIdsList,
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


# HIGH FIX: SSRF protection - validate external URLs before fetching
ALLOWED_IMAGE_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "metadata.google.internal", "169.254.169.254",  # Cloud metadata
    "metadata.aws.amazon.com", "metadata.azure.com",
}
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),       # Private
    ipaddress.ip_network("172.16.0.0/12"),    # Private
    ipaddress.ip_network("192.168.0.0/16"),   # Private
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


def validate_external_url(url: str) -> bool:
    """
    Validate that a URL is safe to fetch (SSRF protection).

    Returns True if URL is safe, False otherwise.
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() not in ALLOWED_IMAGE_SCHEMES:
            logger.warning("Blocked URL with invalid scheme", scheme=parsed.scheme)
            return False

        # Check for blocked hosts
        hostname = parsed.hostname
        if not hostname:
            return False

        hostname_lower = hostname.lower()
        if hostname_lower in BLOCKED_HOSTS:
            logger.warning("Blocked request to internal host", host=hostname)
            return False

        # Check for internal IP addresses
        try:
            ip = ipaddress.ip_address(hostname)
            for blocked_range in BLOCKED_IP_RANGES:
                if ip in blocked_range:
                    logger.warning("Blocked request to internal IP range", ip=str(ip))
                    return False
        except ValueError:
            # Not an IP address, it's a hostname - DNS resolution is handled by httpx
            pass

        return True

    except Exception as e:
        logger.warning("URL validation error", url=url[:100], error=str(e))
        return False


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
                self._face_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.3)
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
            # Use deterministic embedding based on image content hash for consistent comparisons
            import hashlib
            image_hash = hashlib.sha256(image_bytes).digest()
            seed = int.from_bytes(image_hash[:4], 'big')
            rng = np.random.default_rng(seed)
            mock_embedding = rng.standard_normal(512).astype(np.float32)
            mock_embedding = mock_embedding / np.linalg.norm(mock_embedding)  # Normalize
            logger.warning(f"MOCK: Returning deterministic face embedding (seed={seed})")
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
        """Detect all faces in image from URL (with SSRF protection)"""
        # HIGH FIX: Validate URL to prevent SSRF attacks
        if not validate_external_url(image_url):
            logger.warning("Blocked potentially unsafe URL", url=image_url[:100])
            return []

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
        logger.info(f"Liveness check: Starting, image_bytes size={len(image_bytes)}, MOCK={FACE_RECOGNITION_MOCK}")
        await self._initialize()
        logger.info(f"Liveness check: Initialized, _face_app={self._face_app is not None}")

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        logger.info(f"Liveness check: Image decoded, img={img is not None}, shape={img.shape if img is not None else 'None'}")

        if img is None:
            logger.warning("Liveness check: Failed to decode image")
            return False

        if self._face_app is None:
            # In production, InsightFace must be available
            if not FACE_RECOGNITION_MOCK:
                logger.error("Liveness check: InsightFace not available and mock mode disabled")
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

        # Detection confidence threshold
        # NOTE: This is face detection confidence, NOT true liveness detection
        # For production, integrate dedicated liveness service (FaceTec, iProov, AWS Rekognition)
        # Using 0.3 as minimum - faces with lower confidence are likely photos of photos or partial faces
        threshold = 0.3
        passed = bool(det_score > threshold)  # Convert numpy.bool_ to Python bool

        if not passed:
            logger.warning(f"Liveness check failed: score {det_score:.3f} < {threshold}")

        return passed

    async def compare_faces(
        self, embedding1: np.ndarray, embedding2: np.ndarray, threshold: float = None
    ) -> tuple[bool, float]:
        """
        Compare two face embeddings to verify they are the same person.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Minimum similarity threshold (default from settings)

        Returns:
            Tuple of (is_match: bool, similarity_score: float)
        """
        if threshold is None:
            threshold = settings.FACE_SIMILARITY_THRESHOLD

        # In mock mode, always return high similarity since we can't actually verify faces
        # This allows development/testing without InsightFace
        if FACE_RECOGNITION_MOCK:
            mock_similarity = 0.95
            logger.warning(
                f"MOCK: Face comparison returning fixed similarity={mock_similarity:.3f} (threshold={threshold})"
            )
            return True, mock_similarity

        # Calculate cosine similarity (embeddings should be normalized)
        similarity = float(np.dot(embedding1, embedding2))
        is_match = bool(similarity >= threshold)  # Convert to Python bool for JSON serialization

        logger.info(
            f"Face comparison: similarity={similarity:.3f}, threshold={threshold}, match={is_match}"
        )

        return is_match, similarity

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
                points_selector=PointIdsList(points=[str(identity_id)])
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
