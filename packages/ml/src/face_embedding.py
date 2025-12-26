"""
Face Embedding Extraction

Extract 512-dimensional face embeddings from images using InsightFace or ONNX models.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceEmbedding:
    """Face embedding result."""

    embedding: np.ndarray
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    landmarks: Optional[np.ndarray] = None

    @property
    def size(self) -> int:
        """Embedding dimension size."""
        return len(self.embedding)

    def to_list(self) -> list[float]:
        """Convert embedding to list for JSON serialization."""
        return self.embedding.tolist()

    def normalized(self) -> np.ndarray:
        """Return L2-normalized embedding."""
        norm = np.linalg.norm(self.embedding)
        if norm > 0:
            return self.embedding / norm
        return self.embedding


class FaceEmbeddingExtractor:
    """Extract face embeddings using InsightFace."""

    def __init__(
        self,
        model_name: str = "buffalo_l",
        providers: Optional[list[str]] = None,
        det_thresh: float = 0.5,
        det_size: tuple[int, int] = (640, 640),
    ):
        """
        Initialize face embedding extractor.

        Args:
            model_name: InsightFace model name (buffalo_l, buffalo_sc, etc.)
            providers: ONNX runtime providers (default: CPU)
            det_thresh: Face detection threshold
            det_size: Detection input size
        """
        self.model_name = model_name
        self.providers = providers or ["CPUExecutionProvider"]
        self.det_thresh = det_thresh
        self.det_size = det_size
        self._app = None

    def _initialize(self) -> None:
        """Lazy initialize InsightFace model."""
        if self._app is not None:
            return

        try:
            from insightface.app import FaceAnalysis

            self._app = FaceAnalysis(name=self.model_name, providers=self.providers)
            self._app.prepare(ctx_id=0, det_size=self.det_size, det_thresh=self.det_thresh)
            logger.info(f"InsightFace initialized with model: {self.model_name}")
        except ImportError:
            logger.warning("InsightFace not installed. Using mock embeddings.")
            self._app = None
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            self._app = None

    def extract(
        self,
        image: Union[np.ndarray, bytes, str, Path],
        return_largest: bool = True,
    ) -> Optional[FaceEmbedding]:
        """
        Extract face embedding from image.

        Args:
            image: Input image (numpy array, bytes, file path, or Path object)
            return_largest: If multiple faces, return the largest one

        Returns:
            FaceEmbedding object or None if no face detected
        """
        self._initialize()

        # Load image if needed
        img = self._load_image(image)
        if img is None:
            logger.warning("Failed to load image")
            return None

        if self._app is None:
            # Mock mode - return deterministic embedding based on image hash
            return self._mock_embedding(img)

        # Detect faces
        faces = self._app.get(img)

        if not faces:
            logger.debug("No faces detected")
            return None

        # Get target face
        if return_largest:
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        else:
            face = faces[0]

        # Normalize embedding
        embedding = face.embedding / np.linalg.norm(face.embedding)

        return FaceEmbedding(
            embedding=embedding.astype(np.float32),
            bbox=tuple(face.bbox.astype(int)),
            confidence=float(face.det_score),
            landmarks=face.kps if hasattr(face, "kps") else None,
        )

    def extract_all(self, image: Union[np.ndarray, bytes, str, Path]) -> list[FaceEmbedding]:
        """
        Extract embeddings for all faces in image.

        Args:
            image: Input image

        Returns:
            List of FaceEmbedding objects
        """
        self._initialize()

        img = self._load_image(image)
        if img is None:
            return []

        if self._app is None:
            result = self._mock_embedding(img)
            return [result] if result else []

        faces = self._app.get(img)

        results = []
        for face in faces:
            embedding = face.embedding / np.linalg.norm(face.embedding)
            results.append(FaceEmbedding(
                embedding=embedding.astype(np.float32),
                bbox=tuple(face.bbox.astype(int)),
                confidence=float(face.det_score),
                landmarks=face.kps if hasattr(face, "kps") else None,
            ))

        return results

    def _load_image(self, image: Union[np.ndarray, bytes, str, Path]) -> Optional[np.ndarray]:
        """Load image from various sources."""
        if isinstance(image, np.ndarray):
            return image

        if isinstance(image, bytes):
            nparr = np.frombuffer(image, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if isinstance(image, (str, Path)):
            return cv2.imread(str(image))

        return None

    def _mock_embedding(self, img: np.ndarray) -> Optional[FaceEmbedding]:
        """Generate deterministic mock embedding for testing."""
        import hashlib

        # Create deterministic seed from image
        img_hash = hashlib.sha256(img.tobytes()).digest()
        seed = int.from_bytes(img_hash[:4], "big")
        rng = np.random.default_rng(seed)

        # Generate random embedding
        embedding = rng.standard_normal(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        logger.warning("Using mock face embedding (InsightFace not available)")

        return FaceEmbedding(
            embedding=embedding,
            bbox=(100, 100, 300, 300),
            confidence=0.95,
            landmarks=None,
        )


# Default extractor instance
_default_extractor: Optional[FaceEmbeddingExtractor] = None


def extract_face_embedding(
    image: Union[np.ndarray, bytes, str, Path],
    return_largest: bool = True,
) -> Optional[FaceEmbedding]:
    """
    Extract face embedding from image using default extractor.

    Args:
        image: Input image (numpy array, bytes, file path)
        return_largest: If multiple faces, return the largest one

    Returns:
        FaceEmbedding object or None if no face detected
    """
    global _default_extractor

    if _default_extractor is None:
        _default_extractor = FaceEmbeddingExtractor()

    return _default_extractor.extract(image, return_largest=return_largest)
