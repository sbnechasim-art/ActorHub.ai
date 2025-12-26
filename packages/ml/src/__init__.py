"""
ActorHub ML Package

Face recognition, identity verification, and ML utilities for ActorHub.ai
"""

from .face_embedding import FaceEmbedding, extract_face_embedding
from .face_detection import FaceDetector, detect_faces
from .face_comparison import compare_faces, cosine_similarity
from .quality import assess_image_quality, QualityScore
from .liveness import LivenessDetector, check_liveness

__version__ = "1.0.0"

__all__ = [
    # Face Embedding
    "FaceEmbedding",
    "extract_face_embedding",
    # Face Detection
    "FaceDetector",
    "detect_faces",
    # Face Comparison
    "compare_faces",
    "cosine_similarity",
    # Quality Assessment
    "assess_image_quality",
    "QualityScore",
    # Liveness Detection
    "LivenessDetector",
    "check_liveness",
]
