from __future__ import annotations

"""
Multilingual Text Embedder for Semantic Duplicate Detection and Corroboration.
Loads 'intfloat/multilingual-e5-small' via sentence-transformers (384-dimensional).
Per model specification, prepends 'query: ' to texts.

Degrades gracefully to None if sentence-transformers is not installed,
if model weights cannot be downloaded, or if an inference error occurs.
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")
_MODEL_INSTANCE: Any = None
_MODEL_LOAD_ATTEMPTED: bool = False
_MODEL_AVAILABLE: bool = False


def _get_model():
    """
    Lazy-load the SentenceTransformer model instance.
    Safe against missing libraries or download issues.
    """
    global _MODEL_INSTANCE, _MODEL_LOAD_ATTEMPTED, _MODEL_AVAILABLE
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL_INSTANCE

    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _MODEL_INSTANCE = SentenceTransformer(MODEL_NAME)
        _MODEL_AVAILABLE = True
        logger.info("Successfully loaded multilingual embedding model: %s", MODEL_NAME)
    except Exception as e:
        logger.warning(
            "Multilingual embedding model '%s' unavailable (%s). "
            "Semantic embedding will degrade gracefully to Jaccard-only.",
            MODEL_NAME, e
        )
        _MODEL_INSTANCE = None
        _MODEL_AVAILABLE = False

    return _MODEL_INSTANCE


def is_embedder_available() -> bool:
    """Return True if the sentence-transformers model is loaded and ready."""
    return _get_model() is not None


def embed(text: str | None, prefix: str = "query: ") -> list[float] | None:
    """
    Generate a 384-dimensional unit-norm embedding vector for the given text.

    Per intfloat/multilingual-e5-small usage instructions:
    - Stored/indexed documents (e.g. canonical events) must use 'passage: ' prefix.
    - Live queries / incoming event comparisons must use 'query: ' prefix.

    Returns:
        list[float] of length 384, or None if embedder is unavailable
        or if text is empty/whitespace.
    """
    if text is None:
        return None

    cleaned = str(text).strip()
    if not cleaned:
        return None

    model = _get_model()
    if model is None:
        return None

    try:
        # Strip preexisting prefix if different prefix requested or to avoid duplication
        if cleaned.startswith("query: "):
            cleaned = cleaned[7:].strip()
        elif cleaned.startswith("passage: "):
            cleaned = cleaned[9:].strip()

        prefixed = f"{prefix}{cleaned}" if prefix else cleaned
        # normalize_embeddings=True produces unit-length vectors where dot product == cosine similarity
        embedding = model.encode(prefixed, normalize_embeddings=True)
        return [float(x) for x in embedding]
    except Exception as e:
        logger.warning("Embedding inference failed for '%s': %s", cleaned[:40], e)
        return None


def compute_cosine_similarity(
    vec1: list[float] | None,
    vec2: list[float] | None,
) -> float | None:
    """
    Compute cosine similarity between two unit-normalized embedding vectors.

    Returns:
        Float in [0.0, 1.0], or None if either vector is absent or lengths mismatch.
    """
    if not vec1 or not vec2:
        return None
    if len(vec1) != len(vec2) or len(vec1) == 0:
        return None

    # Dot product gives cosine similarity for unit-normalized vectors
    dot = sum(a * b for a, b in zip(vec1, vec2))
    return max(0.0, min(1.0, float(dot)))


def find_similar_canonical_events(
    conn,
    embedding: list[float] | str,
    hours: int = 24,
    limit: int = 5,
    min_similarity: float = 0.70,
) -> list[dict[str, Any]]:
    """
    Query canonical_events within the last N hours ordered by cosine distance
    using pgvector's <=> operator, for use as a corroboration signal.

    Args:
        conn: psycopg2 / PostgreSQL connection.
        embedding: 384-dim float list or pgvector string representation.
        hours: Window of canonical events to query (default 24 hours).
        limit: Maximum results to return (default 5).
        min_similarity: Minimum cosine similarity threshold in [0, 1] (default 0.70).

    Returns:
        List of dicts representing matching canonical events with 'cosine_similarity'.
    """
    if not embedding:
        return []

    vec_str = str(embedding) if isinstance(embedding, (list, tuple)) else str(embedding)

    try:
        with conn.cursor() as cur:
            interval_str = f"{int(hours)} hours"
            cur.execute("""
                SELECT canonical_event_id, event_category, severity, description,
                       city, latitude, longitude, first_seen, last_seen,
                       1 - (embedding <=> %s::vector) AS cosine_similarity
                FROM canonical_events
                WHERE embedding IS NOT NULL
                  AND last_seen >= NOW() - (%s)::interval
                  AND (1 - (embedding <=> %s::vector)) >= %s
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s;
            """, (vec_str, interval_str, vec_str, float(min_similarity), vec_str, int(limit)))

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    except Exception as e:
        logger.warning("pgvector similarity search failed: %s", e)
        return []
