"""
SIH26069 — Multilingual Semantic Duplicate Detection & Embeddings Tests
Validates intfloat/multilingual-e5-small embedder interface, prefix application,
cosine similarity, pgvector query generation, and graceful degradation to Jaccard.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "ml"))
sys.path.insert(0, str(REPO_ROOT / "services" / "ml" / "embeddings"))
sys.path.insert(0, str(REPO_ROOT / "services" / "ml" / "dedup"))

from embeddings.embedder import (
    embed,
    is_embedder_available,
    compute_cosine_similarity,
    find_similar_canonical_events,
)
from dedup.duplicate_detector import (
    compute_duplicate_evidence,
    compute_duplicate_score,
    DUP_WEIGHTS,
)


def test_embed_empty_or_none():
    assert embed(None) is None
    assert embed("") is None
    assert embed("   ") is None


def test_embed_mock_model():
    mock_model = MagicMock()
    # Mock encode returning 384-dimensional unit vector
    dummy_vec = [1.0 / math.sqrt(384)] * 384
    mock_model.encode.return_value = dummy_vec

    with patch("embeddings.embedder._get_model", return_value=mock_model):
        res = embed("Severe flash flood in Mumbai")
        assert res is not None
        assert len(res) == 384
        # Verify query: prefix was added
        mock_model.encode.assert_called_once_with(
            "query: Severe flash flood in Mumbai", normalize_embeddings=True
        )


def test_embed_preserves_existing_prefix():
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1] * 384

    with patch("embeddings.embedder._get_model", return_value=mock_model):
        embed("query: Already prefixed text")
        mock_model.encode.assert_called_once_with(
            "query: Already prefixed text", normalize_embeddings=True
        )


def test_cosine_similarity():
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v1) == 1.0

    # Orthogonal vectors
    v2 = [0.0, 1.0, 0.0]
    assert compute_cosine_similarity(v1, v2) == 0.0

    # Opposite vectors (clamped to 0.0)
    v3 = [-1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v3) == 0.0

    # Dimension mismatch
    assert compute_cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) is None

    # None inputs
    assert compute_cosine_similarity(None, v1) is None
    assert compute_cosine_similarity(v1, None) is None


def test_graceful_degradation_to_jaccard_when_embedder_fails():
    """
    Assert that if embedding model fails / returns None, the duplicate detector
    marks semantic as missing, and produces the exact same score as Jaccard-only.
    """
    event_a = {
        "event_id": "ev-001",
        "event": {"category": "flood", "severity": "high", "description": "Severe flooding near Dadar station"},
        "location": {"latitude": 19.0178, "longitude": 72.8478, "city": "Mumbai"},
        "timestamp": "2026-09-10T12:00:00Z",
        "source_id": "src-100",
        "source_url": "https://news.example.com/flood1",
    }
    event_b = {
        "event_id": "ev-002",
        "event": {"category": "flood", "severity": "high", "description": "Severe flooding around Dadar West station"},
        "location": {"latitude": 19.0180, "longitude": 72.8480, "city": "Mumbai"},
        "timestamp": "2026-09-10T12:05:00Z",
        "source_id": "src-100",
        "source_url": "https://news.example.com/flood1",
    }

    # Ensure embedder returns None (model unavailable)
    with patch("embeddings.embedder._get_model", return_value=None):
        evidence = compute_duplicate_evidence(event_a, event_b)

        assert evidence["signals"]["semantic"] is None
        assert "semantic" in evidence["missing_signals"]
        # Jaccard text similarity must be computed and active
        assert evidence["signals"]["text"] > 0.0
        assert evidence["decision"] in ("probable_duplicate", "possible_duplicate")
        # Ensure final score is in valid [0, 1] range
        assert 0.0 <= evidence["score"] <= 1.0


def test_semantic_signal_integrated_when_embeddings_present():
    """
    When embeddings are provided on both events, 'semantic' is included
    as an additional weighted signal alongside Jaccard.
    """
    emb_a = [1.0, 0.0, 0.0]
    emb_b = [0.8, 0.6, 0.0]  # dot product = 0.8

    event_a = {
        "description": "High water levels on Western Express Highway",
        "category": "flood",
        "embedding": emb_a,
    }
    event_b = {
        "description": "Massive waterlogging along WEH expressway",
        "category": "flood",
        "embedding": emb_b,
    }

    evidence = compute_duplicate_evidence(event_a, event_b)

    assert evidence["signals"]["semantic"] == 0.8
    assert "semantic" not in evidence["missing_signals"]
    # Jaccard is still present and intact
    assert "text" in evidence["signals"]


def test_find_similar_canonical_events_sql():
    mock_cursor = MagicMock()
    mock_cursor.description = [
        ("canonical_event_id",),
        ("event_category",),
        ("severity",),
        ("description",),
        ("city",),
        ("latitude",),
        ("longitude",),
        ("first_seen",),
        ("last_seen",),
        ("cosine_similarity",),
    ]
    mock_cursor.fetchall.return_value = [
        ("ce-111", "flood", "high", "Flooding in Kurla", "Mumbai", 19.07, 72.88, "2026-09-10", "2026-09-10", 0.92)
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    results = find_similar_canonical_events(
        mock_conn,
        embedding=[0.05] * 384,
        hours=12,
        limit=3,
        min_similarity=0.85,
    )

    assert len(results) == 1
    assert results[0]["canonical_event_id"] == "ce-111"
    assert results[0]["cosine_similarity"] == 0.92

    # Verify SQL query executed with <=> operator
    sql_executed = mock_cursor.execute.call_args[0][0]
    assert "<=>" in sql_executed
    assert "canonical_events" in sql_executed


def test_embed_passage_prefix_for_canonical_storage():
    """Verify 'passage: ' prefix is applied when embedding canonical events for storage."""
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.05] * 384

    with patch("embeddings.embedder._get_model", return_value=mock_model):
        res = embed("Heavy flooding in Dadar", prefix="passage: ")
        assert res is not None
        assert len(res) == 384
        mock_model.encode.assert_called_once_with(
            "passage: Heavy flooding in Dadar", normalize_embeddings=True
        )


def test_embed_prefix_switching_strips_existing():
    """Verify switching from query to passage prefix cleanly replaces rather than nests."""
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.05] * 384

    with patch("embeddings.embedder._get_model", return_value=mock_model):
        embed("query: Heavy flooding in Dadar", prefix="passage: ")
        mock_model.encode.assert_called_once_with(
            "passage: Heavy flooding in Dadar", normalize_embeddings=True
        )


def test_precomputed_pgvector_cosine_similarity_consumed():
    """
    Verify that when candidate record contains precomputed cosine_similarity
    from pgvector's <=> operator, duplicate_detector consumes it directly
    without in-memory embedder inference.
    """
    event_curr = {
        "description": "Massive waterlogging along Western Express Highway",
        "category": "flood",
        "latitude": 19.076,
        "longitude": 72.877,
        "timestamp": "2026-09-10T12:00:00Z",
    }
    event_rec = {
        "description": "Severe vehicular flooding and road submerged on expressway",
        "category": "flood",
        "latitude": 19.076,
        "longitude": 72.877,
        "timestamp": "2026-09-10T12:05:00Z",
        "cosine_similarity": 0.885,
    }

    # Model is patched to return None to ensure no in-memory embedder is called
    with patch("embeddings.embedder._get_model", return_value=None):
        evidence = compute_duplicate_evidence(event_curr, event_rec)
        assert evidence["signals"]["semantic"] == 0.885
        assert "semantic" not in evidence["missing_signals"]
        # Jaccard text similarity is also computed and intact (0.0 for paraphrased disjoint text)
        assert evidence["signals"]["text"] == 0.0
        # With semantic similarity, score reaches 0.635 (> 0.60 possible_duplicate threshold)
        assert evidence["score"] == 0.635
        assert evidence["decision"] == "possible_duplicate"
