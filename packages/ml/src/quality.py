"""
Image Quality Assessment Module

Assess face image quality for registration and verification.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Image quality assessment result."""

    overall: float  # 0-100
    sharpness: float  # 0-100
    brightness: float  # 0-100
    contrast: float  # 0-100
    face_size: float  # 0-100 (based on face proportion)
    face_pose: float  # 0-100 (frontal is best)
    is_acceptable: bool

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "sharpness": self.sharpness,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "face_size": self.face_size,
            "face_pose": self.face_pose,
            "is_acceptable": self.is_acceptable,
        }


class QualityAssessor:
    """Assess face image quality."""

    def __init__(
        self,
        min_sharpness: float = 30.0,
        min_brightness: float = 30.0,
        max_brightness: float = 90.0,
        min_contrast: float = 30.0,
        min_face_size_ratio: float = 0.1,
        min_overall: float = 50.0,
    ):
        """
        Initialize quality assessor.

        Args:
            min_sharpness: Minimum sharpness score (0-100)
            min_brightness: Minimum brightness score (0-100)
            max_brightness: Maximum brightness score (0-100)
            min_contrast: Minimum contrast score (0-100)
            min_face_size_ratio: Minimum face-to-image area ratio
            min_overall: Minimum overall score to be acceptable
        """
        self.min_sharpness = min_sharpness
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast
        self.min_face_size_ratio = min_face_size_ratio
        self.min_overall = min_overall

    def assess(
        self,
        image: Union[np.ndarray, bytes, str, Path],
        face_bbox: Optional[tuple[int, int, int, int]] = None,
    ) -> QualityScore:
        """
        Assess image quality.

        Args:
            image: Input image
            face_bbox: Optional face bounding box (x1, y1, x2, y2)

        Returns:
            QualityScore object
        """
        img = self._load_image(image)
        if img is None:
            return QualityScore(
                overall=0, sharpness=0, brightness=0, contrast=0,
                face_size=0, face_pose=0, is_acceptable=False
            )

        # Calculate individual metrics
        sharpness = self._calculate_sharpness(img)
        brightness = self._calculate_brightness(img)
        contrast = self._calculate_contrast(img)
        face_size = self._calculate_face_size(img, face_bbox)
        face_pose = self._estimate_face_pose(img, face_bbox)

        # Calculate overall score (weighted average)
        overall = (
            sharpness * 0.25 +
            self._brightness_score(brightness) * 0.20 +
            contrast * 0.20 +
            face_size * 0.20 +
            face_pose * 0.15
        )

        # Check if acceptable
        is_acceptable = (
            sharpness >= self.min_sharpness and
            brightness >= self.min_brightness and
            brightness <= self.max_brightness and
            contrast >= self.min_contrast and
            overall >= self.min_overall
        )

        return QualityScore(
            overall=round(overall, 1),
            sharpness=round(sharpness, 1),
            brightness=round(brightness, 1),
            contrast=round(contrast, 1),
            face_size=round(face_size, 1),
            face_pose=round(face_pose, 1),
            is_acceptable=is_acceptable,
        )

    def _calculate_sharpness(self, img: np.ndarray) -> float:
        """Calculate image sharpness using Laplacian variance."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Normalize to 0-100 (typical range is 0-3000)
        score = min(100, laplacian_var / 30)
        return score

    def _calculate_brightness(self, img: np.ndarray) -> float:
        """Calculate average brightness."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)

        # Normalize to 0-100
        return brightness / 255 * 100

    def _calculate_contrast(self, img: np.ndarray) -> float:
        """Calculate image contrast using standard deviation."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        contrast = np.std(gray)

        # Normalize to 0-100 (typical range is 0-80)
        return min(100, contrast / 80 * 100)

    def _calculate_face_size(
        self,
        img: np.ndarray,
        face_bbox: Optional[tuple[int, int, int, int]],
    ) -> float:
        """Calculate face size relative to image."""
        img_area = img.shape[0] * img.shape[1]

        if face_bbox is None:
            # Assume face is in center third of image
            return 50.0

        x1, y1, x2, y2 = face_bbox
        face_area = (x2 - x1) * (y2 - y1)
        ratio = face_area / img_area

        # Ideal ratio is around 0.2-0.4
        if ratio < 0.05:
            return 20.0
        elif ratio < 0.1:
            return 50.0
        elif ratio < 0.2:
            return 70.0
        elif ratio < 0.5:
            return 100.0
        else:
            return 80.0  # Face too close

    def _estimate_face_pose(
        self,
        img: np.ndarray,
        face_bbox: Optional[tuple[int, int, int, int]],
    ) -> float:
        """Estimate how frontal the face is."""
        if face_bbox is None:
            return 70.0  # Default

        x1, y1, x2, y2 = face_bbox
        face_width = x2 - x1
        face_height = y2 - y1

        # Aspect ratio check (frontal faces are roughly 1:1.3)
        aspect_ratio = face_width / face_height if face_height > 0 else 1

        ideal_ratio = 0.77  # width/height for frontal face
        ratio_diff = abs(aspect_ratio - ideal_ratio)

        # Score based on how close to ideal ratio
        if ratio_diff < 0.1:
            return 100.0
        elif ratio_diff < 0.2:
            return 80.0
        elif ratio_diff < 0.3:
            return 60.0
        else:
            return 40.0

    def _brightness_score(self, brightness: float) -> float:
        """Convert brightness to quality score (50 is ideal)."""
        # Ideal brightness is around 50
        diff = abs(brightness - 50)
        if diff < 10:
            return 100.0
        elif diff < 20:
            return 80.0
        elif diff < 30:
            return 60.0
        else:
            return 40.0

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


# Default assessor instance
_default_assessor: Optional[QualityAssessor] = None


def assess_image_quality(
    image: Union[np.ndarray, bytes, str, Path],
    face_bbox: Optional[tuple[int, int, int, int]] = None,
) -> QualityScore:
    """
    Assess image quality using default assessor.

    Args:
        image: Input image
        face_bbox: Optional face bounding box

    Returns:
        QualityScore object
    """
    global _default_assessor

    if _default_assessor is None:
        _default_assessor = QualityAssessor()

    return _default_assessor.assess(image, face_bbox)
