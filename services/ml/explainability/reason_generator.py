from __future__ import annotations

"""
Human-Readable Explanation Generator.
Defined in 05_AI_ML_SPEC.md §15.
Generates deterministic, evidence-grounded explanations with zero fabricated claims.
"""

from typing import Any
try:
    from ..credibility.credibility_scorer import generate_credibility_reasons
    from ..utils.event_schema import NormalizedEvent
except ImportError:
    from credibility.credibility_scorer import generate_credibility_reasons
    from utils.event_schema import NormalizedEvent
except (ImportError, ValueError):
    try:
        from credibility.credibility_scorer import generate_credibility_reasons
        from utils.event_schema import NormalizedEvent
    except (ImportError, ValueError):
        from ml.credibility.credibility_scorer import generate_credibility_reasons
        from ml.utils.event_schema import NormalizedEvent


def generate_reasons(
    event: dict | NormalizedEvent | None = None,
    factors: dict | None = None,
    classification: dict | None = None,
    credibility: dict | None = None,
    duplicate_score: float | None = None,
    **kwargs: Any
) -> list[str]:
    """
    Generate unified, human-readable explanations based on actual evidence (§15.1, §15.2).
    """
    if event is None:
        event = kwargs
    norm_event = NormalizedEvent.from_dict(event)

    # 1. If factors dict is provided directly (§15.2 signature)
    if factors:
        corrob_count = int(norm_event.get("corroboration_count", 0)) if hasattr(norm_event, "get") else int(getattr(norm_event, "corroboration_count", 0))
        return generate_credibility_reasons(factors, norm_event, corrob_count)

    reasons = []

    # 2. Classification reasons
    if classification:
        conf = float(classification.get("classification_confidence") or classification.get("confidence", 0.0))
        cat = classification.get("classified_category") or classification.get("category", "other")
        if conf >= 0.80:
            reasons.append(f"Text strongly matches {cat} patterns with high confidence ({conf:.2f})")
        elif conf >= 0.60:
            reasons.append(f"Text matches {cat} patterns with moderate confidence ({conf:.2f})")
        elif conf > 0.0:
            reasons.append(f"Classified as {cat} with low confidence ({conf:.2f})")

    # 3. Credibility reasons
    if credibility:
        cred_reasons = credibility.get("credibility_reasons") or credibility.get("reasons") or []
        for r in cred_reasons:
            if r not in reasons:
                reasons.append(r)

    # 4. Duplicate score reasons
    if duplicate_score is not None:
        dup = float(duplicate_score)
        if dup >= 0.85:
            reasons.append(f"Probable duplicate event detected (duplicate score: {dup:.2f})")
        elif dup >= 0.60:
            reasons.append(f"Possible duplicate report detected (duplicate score: {dup:.2f})")

    if not reasons:
        reasons.append("No specific risk or confidence anomalies detected")

    return reasons