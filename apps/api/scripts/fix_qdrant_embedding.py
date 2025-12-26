"""Fix missing Qdrant embedding for identity"""
import asyncio
import sys
sys.path.insert(0, 'C:/ActorHub.ai 1.1/apps/api')

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# Identity to fix
IDENTITY_ID = "1d94fbd9-a536-4b9f-89a7-502119f9af54"
IMAGE_URL = "http://localhost:9000/actorhub-uploads/identities/00e7b321-0fa1-4461-8203-ab0aed3a5899/fd3c6732-e8c0-4e29-91ae-d79c46c44d3f_face.jpg"

async def main():
    print("Fixing Qdrant embedding...")

    # Connect directly to Qdrant Docker container
    qdrant = QdrantClient(host="localhost", port=6333)

    # Check connection
    collections = qdrant.get_collections()
    print(f"Connected to Qdrant. Collections: {[c.name for c in collections.collections]}")

    # Check current points
    info = qdrant.get_collection("face_embeddings")
    print(f"Current points: {info.points_count}")

    # Download image
    print(f"Downloading image from {IMAGE_URL}...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(IMAGE_URL)
        if resp.status_code != 200:
            print(f"ERROR: Failed to download image: {resp.status_code}")
            return
        image_bytes = resp.content
        print(f"Downloaded {len(image_bytes)} bytes")

    # Try to extract embedding with InsightFace
    try:
        import cv2
        import numpy as np
        from insightface.app import FaceAnalysis

        print("Initializing InsightFace...")
        face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        face_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.3)

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            print("ERROR: Failed to decode image")
            return

        print(f"Image decoded: {img.shape}")

        # Detect faces
        faces = face_app.get(img)
        print(f"Detected {len(faces)} faces")

        if not faces:
            print("ERROR: No face detected")
            return

        # Get embedding of largest face
        largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        embedding = largest_face.embedding
        embedding = embedding / np.linalg.norm(embedding)  # Normalize

        print(f"Extracted embedding: shape={embedding.shape}, norm={np.linalg.norm(embedding):.4f}")

    except ImportError as e:
        print(f"InsightFace not available: {e}")
        print("Using mock embedding (face verification will use mock mode)")
        import numpy as np
        import hashlib

        # Generate deterministic embedding from image
        image_hash = hashlib.sha256(image_bytes).digest()
        seed = int.from_bytes(image_hash[:4], 'big')
        rng = np.random.default_rng(seed)
        embedding = rng.standard_normal(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

    # Store in Qdrant
    print(f"Storing embedding in Qdrant for identity {IDENTITY_ID}...")
    qdrant.upsert(
        collection_name="face_embeddings",
        points=[
            PointStruct(
                id=IDENTITY_ID,
                vector=embedding.tolist(),
                payload={
                    "identity_id": IDENTITY_ID,
                    "created_at": "manual_fix"
                }
            )
        ]
    )

    # Verify
    info = qdrant.get_collection("face_embeddings")
    print(f"SUCCESS! Points in Qdrant: {info.points_count}")

    # Scroll to verify
    results = qdrant.scroll(
        collection_name="face_embeddings",
        limit=10,
        with_payload=True
    )
    print(f"Points: {[p.id for p in results[0]]}")

if __name__ == "__main__":
    asyncio.run(main())
