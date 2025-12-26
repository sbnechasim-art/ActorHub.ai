"""
Face Detection Module

Detect faces in images and return bounding boxes and landmarks.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """Detected face result."""

    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    landmarks: Optional[np.ndarray] = None

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (
            (self.bbox[0] + self.bbox[2]) // 2,
            (self.bbox[1] + self.bbox[3]) // 2,
        )


class FaceDetector:
    """Face detection using OpenCV DNN or InsightFace."""

    def __init__(
        self,
        backend: str = "opencv",
        confidence_threshold: float = 0.5,
        model_path: Optional[str] = None,
    ):
        """
        Initialize face detector.

        Args:
            backend: Detection backend ('opencv', 'insightface', 'mediapipe')
            confidence_threshold: Minimum confidence to consider a detection
            model_path: Optional path to custom model
        """
        self.backend = backend
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path
        self._detector = None

    def _initialize(self) -> None:
        """Initialize detector based on backend."""
        if self._detector is not None:
            return

        if self.backend == "opencv":
            self._init_opencv()
        elif self.backend == "insightface":
            self._init_insightface()
        else:
            logger.warning(f"Unknown backend: {self.backend}, falling back to OpenCV")
            self._init_opencv()

    def _init_opencv(self) -> None:
        """Initialize OpenCV face detector."""
        # Use Haar Cascade as fallback (always available)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._detector = cv2.CascadeClassifier(cascade_path)
        self._detector_type = "haar"
        logger.info("OpenCV Haar Cascade face detector initialized")

    def _init_insightface(self) -> None:
        """Initialize InsightFace detector."""
        try:
            from insightface.app import FaceAnalysis

            self._detector = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
            self._detector.prepare(ctx_id=0, det_size=(320, 320))
            self._detector_type = "insightface"
            logger.info("InsightFace detector initialized")
        except ImportError:
            logger.warning("InsightFace not available, falling back to OpenCV")
            self._init_opencv()

    def detect(
        self,
        image: Union[np.ndarray, bytes, str, Path],
        max_faces: Optional[int] = None,
    ) -> list[DetectedFace]:
        """
        Detect faces in image.

        Args:
            image: Input image
            max_faces: Maximum number of faces to return (largest first)

        Returns:
            List of DetectedFace objects
        """
        self._initialize()

        img = self._load_image(image)
        if img is None:
            return []

        if hasattr(self, "_detector_type") and self._detector_type == "insightface":
            return self._detect_insightface(img, max_faces)
        else:
            return self._detect_opencv(img, max_faces)

    def _detect_opencv(
        self,
        img: np.ndarray,
        max_faces: Optional[int] = None,
    ) -> list[DetectedFace]:
        """Detect faces using OpenCV."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = self._detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )

        results = []
        for x, y, w, h in faces:
            results.append(DetectedFace(
                bbox=(int(x), int(y), int(x + w), int(y + h)),
                confidence=1.0,  # Haar doesn't give confidence
                landmarks=None,
            ))

        # Sort by area (largest first)
        results.sort(key=lambda f: f.area, reverse=True)

        if max_faces:
            results = results[:max_faces]

        return results

    def _detect_insightface(
        self,
        img: np.ndarray,
        max_faces: Optional[int] = None,
    ) -> list[DetectedFace]:
        """Detect faces using InsightFace."""
        faces = self._detector.get(img)

        results = []
        for face in faces:
            if face.det_score < self.confidence_threshold:
                continue

            results.append(DetectedFace(
                bbox=tuple(face.bbox.astype(int)),
                confidence=float(face.det_score),
                landmarks=face.kps if hasattr(face, "kps") else None,
            ))

        # Sort by area (largest first)
        results.sort(key=lambda f: f.area, reverse=True)

        if max_faces:
            results = results[:max_faces]

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


# Default detector instance
_default_detector: Optional[FaceDetector] = None


def detect_faces(
    image: Union[np.ndarray, bytes, str, Path],
    max_faces: Optional[int] = None,
    confidence_threshold: float = 0.5,
) -> list[DetectedFace]:
    """
    Detect faces in image using default detector.

    Args:
        image: Input image
        max_faces: Maximum number of faces to return
        confidence_threshold: Minimum confidence

    Returns:
        List of DetectedFace objects
    """
    global _default_detector

    if _default_detector is None:
        _default_detector = FaceDetector(confidence_threshold=confidence_threshold)

    return _default_detector.detect(image, max_faces=max_faces)
