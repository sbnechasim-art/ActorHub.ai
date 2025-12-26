"""
Face Comparison Module

Compare face embeddings for identity verification.
"""

import logging
from typing import Union

import numpy as np

from .face_embedding import FaceEmbedding

logger = logging.getLogger(__name__)


def cosine_similarity(
    embedding1: Union[np.ndarray, FaceEmbedding],
    embedding2: Union[np.ndarray, FaceEmbedding],
) -> float:
    """
    Calculate cosine similarity between two embeddings.

    Args:
        embedding1: First embedding (array or FaceEmbedding)
        embedding2: Second embedding (array or FaceEmbedding)

    Returns:
        Similarity score between -1 and 1 (higher is more similar)
    """
    if isinstance(embedding1, FaceEmbedding):
        embedding1 = embedding1.embedding
    if isinstance(embedding2, FaceEmbedding):
        embedding2 = embedding2.embedding

    # Normalize embeddings
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    embedding1 = embedding1 / norm1
    embedding2 = embedding2 / norm2

    return float(np.dot(embedding1, embedding2))


def euclidean_distance(
    embedding1: Union[np.ndarray, FaceEmbedding],
    embedding2: Union[np.ndarray, FaceEmbedding],
) -> float:
    """
    Calculate Euclidean distance between two embeddings.

    Args:
        embedding1: First embedding
        embedding2: Second embedding

    Returns:
        Distance (lower is more similar)
    """
    if isinstance(embedding1, FaceEmbedding):
        embedding1 = embedding1.embedding
    if isinstance(embedding2, FaceEmbedding):
        embedding2 = embedding2.embedding

    return float(np.linalg.norm(embedding1 - embedding2))


def compare_faces(
    embedding1: Union[np.ndarray, FaceEmbedding],
    embedding2: Union[np.ndarray, FaceEmbedding],
    threshold: float = 0.4,
    metric: str = "cosine",
) -> dict:
    """
    Compare two face embeddings and determine if they match.

    Args:
        embedding1: First face embedding
        embedding2: Second face embedding
        threshold: Similarity threshold for match (depends on metric)
        metric: Comparison metric ('cosine' or 'euclidean')

    Returns:
        Dictionary with match result and scores
    """
    if metric == "cosine":
        similarity = cosine_similarity(embedding1, embedding2)
        is_match = similarity >= threshold
        return {
            "is_match": is_match,
            "similarity": similarity,
            "distance": 1 - similarity,
            "threshold": threshold,
            "metric": "cosine",
        }
    elif metric == "euclidean":
        distance = euclidean_distance(embedding1, embedding2)
        # For euclidean, lower is better
        is_match = distance <= threshold
        return {
            "is_match": is_match,
            "similarity": max(0, 1 - distance / 2),  # Rough conversion to similarity
            "distance": distance,
            "threshold": threshold,
            "metric": "euclidean",
        }
    else:
        raise ValueError(f"Unknown metric: {metric}")


def find_best_match(
    query_embedding: Union[np.ndarray, FaceEmbedding],
    gallery_embeddings: list[Union[np.ndarray, FaceEmbedding]],
    gallery_ids: list[str],
    threshold: float = 0.4,
) -> dict:
    """
    Find the best matching face in a gallery.

    Args:
        query_embedding: Query face embedding
        gallery_embeddings: List of gallery embeddings
        gallery_ids: List of IDs corresponding to gallery embeddings
        threshold: Minimum similarity to consider a match

    Returns:
        Dictionary with best match result
    """
    if len(gallery_embeddings) == 0:
        return {
            "matched": False,
            "identity_id": None,
            "similarity": 0.0,
            "rank": -1,
        }

    similarities = []
    for emb in gallery_embeddings:
        sim = cosine_similarity(query_embedding, emb)
        similarities.append(sim)

    best_idx = int(np.argmax(similarities))
    best_similarity = similarities[best_idx]

    is_match = best_similarity >= threshold

    return {
        "matched": is_match,
        "identity_id": gallery_ids[best_idx] if is_match else None,
        "similarity": float(best_similarity),
        "rank": 1 if is_match else -1,
        "all_scores": [
            {"id": gid, "similarity": float(sim)}
            for gid, sim in zip(gallery_ids, similarities)
        ],
    }


def batch_compare(
    embeddings: list[Union[np.ndarray, FaceEmbedding]],
    threshold: float = 0.4,
) -> np.ndarray:
    """
    Compute pairwise similarity matrix for a batch of embeddings.

    Args:
        embeddings: List of embeddings
        threshold: Similarity threshold (not used in matrix, just for reference)

    Returns:
        NxN similarity matrix
    """
    n = len(embeddings)
    matrix = np.zeros((n, n))

    # Convert all to numpy arrays
    arrays = []
    for emb in embeddings:
        if isinstance(emb, FaceEmbedding):
            arrays.append(emb.normalized())
        else:
            norm = np.linalg.norm(emb)
            arrays.append(emb / norm if norm > 0 else emb)

    # Compute pairwise similarities
    for i in range(n):
        for j in range(i, n):
            sim = float(np.dot(arrays[i], arrays[j]))
            matrix[i, j] = sim
            matrix[j, i] = sim

    return matrix
