# ActorHub ML Package

Machine Learning utilities for ActorHub.ai - Face Recognition & Identity Verification.

## Installation

```bash
# Basic installation
pip install actorhub-ml

# With InsightFace support
pip install actorhub-ml[insightface]

# With GPU support
pip install actorhub-ml[gpu]

# Full installation
pip install actorhub-ml[full]
```

## Quick Start

### Face Embedding Extraction

```python
from actorhub_ml import extract_face_embedding

# From file
embedding = extract_face_embedding("photo.jpg")
print(f"Embedding shape: {embedding.size}")  # 512

# From bytes
with open("photo.jpg", "rb") as f:
    embedding = extract_face_embedding(f.read())
```

### Face Detection

```python
from actorhub_ml import detect_faces

faces = detect_faces("group_photo.jpg")
for face in faces:
    print(f"Face at {face.bbox}, confidence: {face.confidence}")
```

### Face Comparison

```python
from actorhub_ml import extract_face_embedding, compare_faces

emb1 = extract_face_embedding("person1.jpg")
emb2 = extract_face_embedding("person2.jpg")

result = compare_faces(emb1, emb2, threshold=0.4)
print(f"Match: {result['is_match']}, Similarity: {result['similarity']:.2f}")
```

### Image Quality Assessment

```python
from actorhub_ml import assess_image_quality

quality = assess_image_quality("selfie.jpg")
print(f"Overall score: {quality.overall}")
print(f"Acceptable: {quality.is_acceptable}")
print(f"Sharpness: {quality.sharpness}")
print(f"Brightness: {quality.brightness}")
```

### Liveness Detection

```python
from actorhub_ml import check_liveness

result = check_liveness("webcam_frame.jpg")
print(f"Is live: {result.is_live}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Message: {result.message}")
```

## API Reference

### FaceEmbedding

```python
@dataclass
class FaceEmbedding:
    embedding: np.ndarray  # 512-dimensional vector
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    landmarks: Optional[np.ndarray]
```

### QualityScore

```python
@dataclass
class QualityScore:
    overall: float  # 0-100
    sharpness: float
    brightness: float
    contrast: float
    face_size: float
    face_pose: float
    is_acceptable: bool
```

### LivenessResult

```python
@dataclass
class LivenessResult:
    is_live: bool
    confidence: float  # 0-1
    checks: dict[str, bool]
    message: str
```

## Configuration

### Face Embedding Extractor

```python
from actorhub_ml.face_embedding import FaceEmbeddingExtractor

extractor = FaceEmbeddingExtractor(
    model_name="buffalo_l",  # or "buffalo_sc" for smaller model
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    det_thresh=0.5,
    det_size=(640, 640),
)
```

### Quality Assessor

```python
from actorhub_ml.quality import QualityAssessor

assessor = QualityAssessor(
    min_sharpness=30.0,
    min_brightness=30.0,
    max_brightness=90.0,
    min_contrast=30.0,
    min_face_size_ratio=0.1,
    min_overall=50.0,
)
```

## Models

The package uses InsightFace models by default:

- **buffalo_l**: Large model, best accuracy (~50MB)
- **buffalo_sc**: Small model, faster (~15MB)

Models are downloaded automatically on first use.

## License

MIT License - See LICENSE for details.
