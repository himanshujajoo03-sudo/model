from __future__ import annotations

"""
Multilingual Text Embeddings Package.
Uses intfloat/multilingual-e5-small (384-dimensional) with pgvector integration.
"""

from .embedder import (
    embed,
    is_embedder_available,
    compute_cosine_similarity,
    find_similar_canonical_events,
)

__all__ = [
    "embed",
    "is_embedder_available",
    "compute_cosine_similarity",
    "find_similar_canonical_events",
]
