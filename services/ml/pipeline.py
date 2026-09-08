from __future__ import annotations

"""Canonical ML enrichment stage for the Spark -> AI/ML -> storage flow.

Upstream responsibilities (Kafka/Spark) are validation, streaming
watermarks/deduplication, and windowed aggregation. This module starts after
those stages and performs the AI/ML enrichment in a deterministic order:
classification -> duplicate evidence -> credibility -> clustering ->
explainability.
"""

from copy import deepcopy
from typing import Any

try:
    from .classifier.event_classifier import classify_event
    from .credibility.credibility_scorer import score_credibility
    from .dedup.duplicate_detector import compute_duplicate_evidence
    from .clustering.event_clusterer import assign_cluster
    from .explainability.reason_generator import generate_reasons
    from .utils.event_schema import NormalizedEvent, EventValidationError
except ImportError:
    from classifier.event_classifier import classify_event
    from credibility.credibility_scorer import score_credibility
    from dedup.duplicate_detector import compute_duplicate_evidence
    from clustering.event_clusterer import assign_cluster
    from explainability.reason_generator import generate_reasons
    from utils.event_schema import NormalizedEvent, EventValidationError
except (ImportError, ValueError):
    try:
        from classifier.event_classifier import classify_event
        from credibility.credibility_scorer import score_credibility
        from dedup.duplicate_detector import compute_duplicate_evidence
        from clustering.event_clusterer import assign_cluster
        from explainability.reason_generator import generate_reasons
        from utils.event_schema import NormalizedEvent, EventValidationError
    except (ImportError, ValueError):
        from ml.classifier.event_classifier import classify_event
        from ml.credibility.credibility_scorer import score_credibility
        from ml.dedup.duplicate_detector import compute_duplicate_evidence
        from ml.clustering.event_clusterer import assign_cluster
        from ml.explainability.reason_generator import generate_reasons
        from ml.utils.event_schema import NormalizedEvent, EventValidationError


def enrich_event(
    event: dict | NormalizedEvent,
    recent_events: list[dict | NormalizedEvent] | None = None,
    active_clusters: list[dict] | None = None,
    *,
    strict_validation: bool = False,
    auto_create_cluster: bool = False,
) -> dict:
    """Run the complete ML enrichment stage for one canonical event.

    The function never mutates the caller's dictionary. It returns the original
    event fields plus a canonical ``ai`` object and top-level compatibility
    fields. Invalid required coordinates are rejected only when
    ``strict_validation=True``; missing coordinates are allowed because
    clustering and spatial scoring explicitly support incomplete reports.
    """
    if not isinstance(event, (dict, NormalizedEvent)):
        raise TypeError("event must be a dict or NormalizedEvent")

    raw = deepcopy(event.to_dict() if isinstance(event, NormalizedEvent) else event)
    normalized = NormalizedEvent.from_dict(raw, strict=strict_validation)
    recent = recent_events or []

    classification = classify_event(normalized.description, normalized.category)
    classified_category = classification.get("classified_category", "other")
    classification_confidence = float(classification.get("classification_confidence", 0.0) or 0.0)

    # Use the classified category for downstream semantic comparisons without
    # destroying the source adapter's original category in the raw payload.
    working = normalized.to_dict()
    working["category"] = classified_category
    working["ai"] = {**raw.get("ai", {})} if isinstance(raw.get("ai"), dict) else {}
    working["ai"].update(classification)

    duplicate_evidence = {"score": 0.0, "decision": "not_duplicate", "signals": {}, "missing_signals": []}
    if recent:
        duplicate_scores = [compute_duplicate_evidence(working, candidate) for candidate in recent]
        duplicate_evidence = max(duplicate_scores, key=lambda x: x["score"])

    credibility = score_credibility(working, recent)

    cluster_id = assign_cluster(
        working,
        active_clusters=active_clusters,
        auto_generate_on_none=auto_create_cluster,
    )

    ai = working["ai"]
    ai.update({
        "duplicate_score": duplicate_evidence["score"],
        "duplicate_decision": duplicate_evidence["decision"],
        "duplicate_signals": duplicate_evidence["signals"],
        "duplicate_missing_signals": duplicate_evidence["missing_signals"],
        "credibility_score": credibility["credibility_score"],
        "credibility_reasons": credibility["credibility_reasons"],
        "credibility_factors": credibility["factors"],
    })
    if cluster_id is not None:
        ai["cluster_id"] = str(cluster_id)

    ai["explanation"] = generate_reasons(
        event=working,
        classification=classification,
        credibility=credibility,
        duplicate_score=duplicate_evidence["score"],
    )

    # Preserve the canonical top-level fields expected by existing consumers.
    result = dict(raw)
    result.update({
        "category": classified_category,
        "confidence": classification_confidence,
        "ai": ai,
    })
    result["classified_category"] = classified_category
    result["classification_confidence"] = classification_confidence
    result["credibility_score"] = credibility["credibility_score"]
    result["duplicate_score"] = duplicate_evidence["score"]
    if cluster_id is not None:
        result["cluster_id"] = str(cluster_id)
    result["credibility_reasons"] = credibility["credibility_reasons"]
    result["explanation"] = ai["explanation"]
    return result


__all__ = ["enrich_event"]
