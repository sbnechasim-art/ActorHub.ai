"""
Liveness Detection Module

Detect if a face is from a live person vs a photo/video replay attack.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LivenessResult:
    """Liveness detection result."""

    is_live: bool
    confidence: float  # 0-1
    checks: dict[str, bool]
    message: str


class LivenessDetector:
    """
    Passive liveness detection using image analysis.

    Note: For production use, consider active liveness challenges
    (blink detection, head movement) or specialized anti-spoofing models.
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        texture_threshold: float = 20.0,
        color_threshold: float = 10.0,
    ):
        """
        Initialize liveness detector.

        Args:
            min_confidence: Minimum confidence to consider live
            texture_threshold: Minimum texture variation
            color_threshold: Minimum color variation for skin tone
        """
        self.min_confidence = min_confidence
        self.texture_threshold = texture_threshold
        self.color_threshold = color_threshold

    def detect(
        self,
        image: Union[np.ndarray, bytes, str, Path],
        face_bbox: Optional[tuple[int, int, int, int]] = None,
    ) -> LivenessResult:
        """
        Detect if image contains a live face.

        Args:
            image: Input image
            face_bbox: Optional face bounding box

        Returns:
            LivenessResult object
        """
        img = self._load_image(image)
        if img is None:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                checks={},
                message="Failed to load image",
            )

        # Extract face region
        if face_bbox:
            x1, y1, x2, y2 = face_bbox
            face_img = img[y1:y2, x1:x2]
        else:
            # Use center region as approximation
            h, w = img.shape[:2]
            face_img = img[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]

        # Run checks
        checks = {}

        # 1. Texture analysis (photos often have different texture)
        checks["texture"] = self._check_texture(face_img)

        # 2. Color distribution (natural skin has specific distribution)
        checks["color"] = self._check_color_distribution(face_img)

        # 3. Reflection/glare detection
        checks["reflection"] = self._check_reflections(face_img)

        # 4. Moire pattern detection (screens)
        checks["moire"] = self._check_moire(face_img)

        # 5. Edge analysis (printed photos have different edges)
        checks["edges"] = self._check_edges(face_img)

        # Calculate confidence
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        confidence = passed_checks / total_checks

        is_live = confidence >= self.min_confidence

        if is_live:
            message = "Face appears to be live"
        else:
            failed = [k for k, v in checks.items() if not v]
            message = f"Potential spoof detected: {', '.join(failed)}"

        return LivenessResult(
            is_live=is_live,
            confidence=confidence,
            checks=checks,
            message=message,
        )

    def _check_texture(self, face_img: np.ndarray) -> bool:
        """Check face texture using Local Binary Patterns variance."""
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)

        # Calculate LBP-like texture measure
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        texture_var = laplacian.var()

        return texture_var > self.texture_threshold

    def _check_color_distribution(self, face_img: np.ndarray) -> bool:
        """Check if color distribution matches natural skin tones."""
        # Convert to YCrCb (better for skin detection)
        ycrcb = cv2.cvtColor(face_img, cv2.COLOR_BGR2YCrCb)

        # Typical skin color ranges in YCrCb
        # Cr: 133-173, Cb: 77-127
        cr = ycrcb[:, :, 1]
        cb = ycrcb[:, :, 2]

        cr_std = np.std(cr)
        cb_std = np.std(cb)

        # Natural skin has some variation
        has_variation = cr_std > self.color_threshold and cb_std > self.color_threshold

        # Check if majority is in skin range
        skin_mask = (cr > 133) & (cr < 173) & (cb > 77) & (cb < 127)
        skin_ratio = np.sum(skin_mask) / skin_mask.size

        return has_variation and skin_ratio > 0.3

    def _check_reflections(self, face_img: np.ndarray) -> bool:
        """Check for unnatural reflections (screen/photo glare)."""
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)

        # Find very bright spots (potential reflections)
        bright_threshold = 240
        bright_spots = gray > bright_threshold
        bright_ratio = np.sum(bright_spots) / bright_spots.size

        # Some bright spots are normal, too many indicate screen/photo
        return bright_ratio < 0.05

    def _check_moire(self, face_img: np.ndarray) -> bool:
        """Check for moire patterns (indicates screen capture)."""
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)

        # Apply FFT to detect periodic patterns
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)

        # Remove DC component
        h, w = magnitude.shape
        magnitude[h // 2 - 5 : h // 2 + 5, w // 2 - 5 : w // 2 + 5] = 0

        # Check for strong periodic patterns
        max_mag = np.max(magnitude)
        mean_mag = np.mean(magnitude)

        # Moire patterns create strong periodic peaks
        ratio = max_mag / mean_mag if mean_mag > 0 else 0
        return ratio < 100  # No strong periodic patterns

    def _check_edges(self, face_img: np.ndarray) -> bool:
        """Check edge characteristics (printed photos have different edges)."""
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Natural faces have moderate edge density
        return 0.02 < edge_density < 0.15

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
_default_detector: Optional[LivenessDetector] = None


def check_liveness(
    image: Union[np.ndarray, bytes, str, Path],
    face_bbox: Optional[tuple[int, int, int, int]] = None,
) -> LivenessResult:
    """
    Check liveness using default detector.

    Args:
        image: Input image
        face_bbox: Optional face bounding box

    Returns:
        LivenessResult object
    """
    global _default_detector

    if _default_detector is None:
        _default_detector = LivenessDetector()

    return _default_detector.detect(image, face_bbox)
