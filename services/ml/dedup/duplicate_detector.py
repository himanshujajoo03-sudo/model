from __future__ import annotations

"""
Duplicate Weather Report Detector.
Defined in 05_AI_ML_SPEC.md §11, §12.
Configurable weights and thresholds from centralized ml_config.yaml.
"""

from typing import Any, Optional
try:
    from ..classifier.rules import categories_are_compatible, canonicalize_category
    from ..config.config_loader import load_ml_config
    from ..utils.event_schema import NormalizedEvent
    from ..utils.geo import haversine_km
    from ..utils.text import text_similarity
    from ..utils.time_utils import time_diff_minutes
except ImportError:
    from classifier.rules import categories_are_compatible, canonicalize_category
    from config.config_loader import load_ml_config
    from utils.event_schema import NormalizedEvent
    from utils.geo import haversine_km
    from utils.text import text_similarity
    from utils.time_utils import time_diff_minutes
except (ImportError, ValueError):
    try:
        from classifier.rules import categories_are_compatible, canonicalize_category
        from config.config_loader import load_ml_config
        from utils.event_schema import NormalizedEvent
        from utils.geo import haversine_km
        from utils.text import text_similarity
        from utils.time_utils import time_diff_minutes
    except (ImportError, ValueError):
        from ml.classifier.rules import categories_are_compatible, canonicalize_category
        from ml.config.config_loader import load_ml_config
        from ml.utils.event_schema import NormalizedEvent
        from ml.utils.geo import haversine_km
        from ml.utils.text import text_similarity
        from ml.utils.time_utils import time_diff_minutes

# §11.2 Default Weights (Backward Compatibility)
DUP_WEIGHTS = {
    "text": 0.30,
    "source_id": 0.20,
    "source_url": 0.15,
    "category": 0.15,
    "time": 0.10,
    "distance": 0.10,
    "semantic": 0.25,
}


def get_duplicate_config() -> dict[str, Any]:
    """Load validated duplicate weights and thresholds from centralized config."""
    cfg = load_ml_config()
    dup = cfg.get("duplicate", {})
    weights = dup.get("weights", DUP_WEIGHTS)
    return {
        "weights": {
            "text": float(weights.get("text", 0.30)),
            "source_id": float(weights.get("source_id", 0.20)),
            "source_url": float(weights.get("source_url", 0.15)),
            "category": float(weights.get("category", 0.15)),
            "time": float(weights.get("time", 0.10)),
            "distance": float(weights.get("distance", 0.10)),
            "semantic": float(weights.get("semantic", 0.25)),
        },
        "probable_threshold": float(dup.get("probable_threshold", 0.85)),
        "possible_threshold": float(dup.get("possible_threshold", 0.60)),
    }


def time_difference_score(minutes_diff: float) -> float:
    """Score based on time difference between events (§11.4)."""
    if minutes_diff <= 5.0:
        return 1.0
    elif minutes_diff <= 30.0:
        return 0.8
    elif minutes_diff <= 60.0:
        return 0.5
    elif minutes_diff <= 180.0:
        return 0.2
    else:
        return 0.0


def geographic_distance_score(distance_km: float) -> float:
    """Score based on distance between events in km (§11.5)."""
    if distance_km <= 0.5:
        return 1.0
    elif distance_km <= 2.0:
        return 0.8
    elif distance_km <= 5.0:
        return 0.5
    elif distance_km <= 10.0:
        return 0.2
    else:
        return 0.0


def category_match_score(cat1: str | None, cat2: str | None) -> float:
    """Score category match (§11.2)."""
    c1 = canonicalize_category(cat1, strict=False)
    c2 = canonicalize_category(cat2, strict=False)
    if not c1 or not c2:
        return 0.0
    if c1 == c2 and c1 != "other":
        return 1.0
    elif categories_are_compatible(c1, c2):
        return 0.5
    return 0.0


def compute_duplicate_evidence(
    current: dict | NormalizedEvent,
    recent: dict | NormalizedEvent
) -> dict[str, Any]:
    """
    Compute duplicate similarity evidence between two events (§11, §15, §16
    hardening pass 2).

    Missing-data semantics (Rule 15): a missing timestamp, missing
    coordinates, or missing source URL is NOT treated as evidence AGAINST a
    duplicate (i.e. NOT scored as "very different"/"very far away"). Instead,
    that signal is marked unavailable and excluded from scoring, with the
    remaining available signal weights renormalized to sum to 1.0. This
    avoids systematically under-scoring duplicate reports simply because one
    of them lacks optional metadata.

    Text similarity and category are always considered "available" signals
    (an event always has *some* description/category, even if empty), so
    they are never excluded by this renormalization.

    Returns a structured evidence dict (Rule 16):
        {
            "score": float,
            "decision": "probable_duplicate" | "possible_duplicate" | "not_duplicate",
            "signals": {"text": .., "source_id": .., ...},   # None if unavailable
            "missing_signals": [...],
        }
    """
    curr = NormalizedEvent.from_dict(current)
    rec = NormalizedEvent.from_dict(recent)

    dup_cfg = get_duplicate_config()
    weights = dict(dup_cfg["weights"])

    signals: dict[str, Optional[float]] = {}
    missing_signals: list[str] = []

    # 1. Text similarity -- always available (description defaults to "")
    signals["text"] = text_similarity(curr.description, rec.description)

    # 2. Source ID match -- only meaningful if both sides supplied one
    if curr.source_id and rec.source_id:
        signals["source_id"] = 1.0 if curr.source_id == rec.source_id else 0.0
    else:
        signals["source_id"] = None
        missing_signals.append("source_id")

    # 3. Source URL match -- only meaningful if both sides supplied one
    if curr.source_url and rec.source_url:
        signals["source_url"] = 1.0 if curr.source_url == rec.source_url else 0.0
    else:
        signals["source_url"] = None
        missing_signals.append("source_url")

    # 4. Category match -- always available (category_match_score handles None gracefully)
    signals["category"] = category_match_score(curr.category, rec.category)

    # 5. Time difference -- only meaningful if both timestamps are present
    if curr.timestamp is not None and rec.timestamp is not None:
        diff_min = time_diff_minutes(curr.timestamp, rec.timestamp)
        signals["time"] = time_difference_score(diff_min)
    else:
        signals["time"] = None
        missing_signals.append("time")

    # 6. Geographic distance -- only meaningful if both coordinate pairs are present
    if curr.latitude is not None and curr.longitude is not None and rec.latitude is not None and rec.longitude is not None:
        dist_km = haversine_km(curr.latitude, curr.longitude, rec.latitude, rec.longitude)
        signals["distance"] = geographic_distance_score(dist_km)
    else:
        signals["distance"] = None
        missing_signals.append("distance")

    # 7. Semantic embedding similarity -- optional signal alongside Jaccard text (§11)
    # Check if a precomputed cosine similarity from pgvector <=> search is available on the candidate record
    precomputed_sem = None
    if hasattr(rec, "raw") and isinstance(rec.raw, dict):
        precomputed_sem = rec.raw.get("cosine_similarity") if rec.raw.get("cosine_similarity") is not None else rec.raw.get("semantic_similarity")
    if precomputed_sem is None and isinstance(recent, dict):
        precomputed_sem = recent.get("cosine_similarity") if recent.get("cosine_similarity") is not None else recent.get("semantic_similarity")

    if precomputed_sem is not None:
        try:
            sem_sim = max(0.0, min(1.0, float(precomputed_sem)))
            signals["semantic"] = round(sem_sim, 3)
        except (ValueError, TypeError):
            signals["semantic"] = None
    else:
        # Fall back to in-memory embedding calculation if precomputed pgvector similarity is absent
        curr_emb = getattr(curr, "embedding", None) or (curr.raw.get("embedding") if isinstance(getattr(curr, "raw", None), dict) else None)
        rec_emb = getattr(rec, "embedding", None) or (rec.raw.get("embedding") if isinstance(getattr(rec, "raw", None), dict) else None)

        # If embeddings are not attached, attempt lazy generation via embedder if available
        # Incoming events use "query: ", stored/historical events use "passage: "
        if curr_emb is None and curr.description:
            try:
                from ..embeddings.embedder import embed
                curr_emb = embed(curr.description, prefix="query: ")
            except Exception:
                try:
                    from embeddings.embedder import embed
                    curr_emb = embed(curr.description, prefix="query: ")
                except Exception:
                    curr_emb = None

        if rec_emb is None and rec.description:
            try:
                from ..embeddings.embedder import embed
                rec_emb = embed(rec.description, prefix="passage: ")
            except Exception:
                try:
                    from embeddings.embedder import embed
                    rec_emb = embed(rec.description, prefix="passage: ")
                except Exception:
                    rec_emb = None

        if curr_emb and rec_emb and len(curr_emb) == len(rec_emb) and len(curr_emb) > 0:
            try:
                from ..embeddings.embedder import compute_cosine_similarity
                sem_sim = compute_cosine_similarity(curr_emb, rec_emb)
            except Exception:
                try:
                    from embeddings.embedder import compute_cosine_similarity
                    sem_sim = compute_cosine_similarity(curr_emb, rec_emb)
                except Exception:
                    dot = sum(a * b for a, b in zip(curr_emb, rec_emb))
                    sem_sim = max(0.0, min(1.0, float(dot)))
            signals["semantic"] = round(sem_sim, 3) if sem_sim is not None else None
        else:
            signals["semantic"] = None

    if signals["semantic"] is None:
        missing_signals.append("semantic")

    # Renormalize weights across only the AVAILABLE signals
    available_weight_sum = sum(weights[k] for k, v in signals.items() if v is not None)
    if available_weight_sum <= 0.0:
        # Degenerate case: nothing usable at all besides text (should not
        # normally happen since text/category are always available).
        score = 0.0
    else:
        score = sum(
            (weights[k] / available_weight_sum) * v
            for k, v in signals.items()
            if v is not None
        )

    score = round(min(max(score, 0.0), 1.0), 3)

    dup_cfg2 = get_duplicate_config()
    if score >= dup_cfg2["probable_threshold"]:
        decision = "probable_duplicate"
    elif score >= dup_cfg2["possible_threshold"]:
        decision = "possible_duplicate"
    else:
        decision = "not_duplicate"

    return {
        "score": score,
        "decision": decision,
        "signals": signals,
        "missing_signals": missing_signals,
    }


def compute_pairwise_duplicate_score(
    current: dict | NormalizedEvent,
    recent: dict | NormalizedEvent
) -> float:
    """
    Compute duplicate similarity score between two events.

    Backward-compatible thin wrapper around `compute_duplicate_evidence` that
    returns just the numeric score, as this function historically did.
    """
    return compute_duplicate_evidence(current, recent)["score"]


def compute_duplicate_score(
    current: dict | NormalizedEvent,
    recent_events: list[dict | NormalizedEvent] | dict | NormalizedEvent | None = None,
    **kwargs: Any
) -> float:
    """
    Compute duplicate score against recent events window (§11.6).
    If recent_events is a single dict or NormalizedEvent, performs pairwise scoring.
    """
    if recent_events is None:
        return 0.0

    # Handle pairwise invocation
    if isinstance(recent_events, (dict, NormalizedEvent)):
        return compute_pairwise_duplicate_score(current, recent_events)

    if not recent_events:
        return 0.0

    scores = [compute_pairwise_duplicate_score(current, rec) for rec in recent_events]
    return round(max(scores), 3)


def is_duplicate(duplicate_score: float, threshold: float | None = None) -> bool:
    """Probable duplicate check (§12.1)."""
    if threshold is None:
        threshold = get_duplicate_config()["probable_threshold"]
    return float(duplicate_score or 0.0) >= float(threshold)


def is_review_candidate(
    duplicate_score: float,
    review_threshold: float | None = None,
    duplicate_threshold: float | None = None
) -> bool:
    """Possible duplicate check for admin review (§12.1)."""
    dup_cfg = get_duplicate_config()
    if review_threshold is None:
        review_threshold = dup_cfg["possible_threshold"]
    if duplicate_threshold is None:
        duplicate_threshold = dup_cfg["probable_threshold"]

    score = float(duplicate_score or 0.0)
    return float(review_threshold) <= score < float(duplicate_threshold)
