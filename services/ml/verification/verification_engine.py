from __future__ import annotations

"""
Deterministic Verification Decision Engine.
Defined in SIH26069_SETUP.md §14.4 and 05_AI_ML_SPEC.md.
Convergent evidence decision policy:
- Requires multiple positive signals
- Conservative: prefers needs_review over incorrect verification
- Explains every decision with human-readable reasons
"""

from typing import Optional, List, Tuple, Any

# Valid statuses per database constraints (init.sql and 02_canonical_events.sql)
VALID_STATUSES = ("pending", "verified", "needs_review", "suspicious", "duplicate")

def decide_verification(
    credibility_score: Optional[float] = None,
    duplicate_score: Optional[float] = None,
    corroboration: Optional[int] = None,
    source_trust: Optional[float] = None,
    spatial_consistency: Optional[float] = None,
    temporal_consistency: Optional[float] = None,
    classification_confidence: Optional[float] = None,
    weather_agreement: Optional[float] = None,
    source_type: Optional[str] = None,
    **kwargs: Any,
) -> Tuple[str, List[str]]:
    """
    Decide the verification status and generate explainable reasons.

    Returns:
        (status, reasons)
        where status is in ('pending', 'verified', 'needs_review', 'suspicious', 'duplicate')
    """
    reasons: List[str] = []
    positive_signals = 0
    negative_signals = 0

    # 1. Duplicate check (Highest precedence: duplicate >= 0.85 per spec)
    if duplicate_score is not None and duplicate_score >= 0.85:
        reasons.append(f"High duplicate probability ({duplicate_score:.2f} >= 0.85)")
        return "duplicate", reasons

    # 2. Evaluate positive signals
    if credibility_score is not None and credibility_score >= 0.70:
        positive_signals += 1
        reasons.append(f"High credibility score ({credibility_score:.2f})")

    if corroboration is not None and corroboration >= 2:
        positive_signals += 1
        reasons.append(f"Multiple independent corroborations ({corroboration} sources)")

    if source_trust is not None and source_trust >= 0.80:
        positive_signals += 1
        source_label = f" ({source_type})" if source_type else ""
        reasons.append(f"Authoritative source trust{source_label} ({source_trust:.2f})")

    if weather_agreement is not None and weather_agreement >= 0.70:
        positive_signals += 1
        reasons.append(f"Strong meteorological agreement ({weather_agreement:.2f})")

    if spatial_consistency is not None and spatial_consistency >= 0.80:
        positive_signals += 1
        reasons.append(f"High spatial consistency ({spatial_consistency:.2f})")

    if temporal_consistency is not None and temporal_consistency >= 0.80:
        positive_signals += 1
        reasons.append(f"High temporal consistency ({temporal_consistency:.2f})")

    if classification_confidence is not None and classification_confidence >= 0.80:
        positive_signals += 1
        reasons.append(f"High classification confidence ({classification_confidence:.2f})")

    # 3. Evaluate negative signals
    if credibility_score is not None and credibility_score < 0.35:
        negative_signals += 1
        reasons.append(f"Low credibility score ({credibility_score:.2f})")

    if weather_agreement is not None and weather_agreement < 0.30:
        negative_signals += 1
        reasons.append(f"Poor weather agreement ({weather_agreement:.2f})")

    if source_trust is not None and source_trust < 0.35:
        negative_signals += 1
        reasons.append(f"Untrusted source ({source_trust:.2f})")

    if spatial_consistency is not None and spatial_consistency < 0.30:
        negative_signals += 1
        reasons.append(f"Geographic discrepancy ({spatial_consistency:.2f})")

    if temporal_consistency is not None and temporal_consistency < 0.30:
        negative_signals += 1
        reasons.append(f"Temporal inconsistency ({temporal_consistency:.2f})")

    # 4. Synthesize decision
    if negative_signals >= 2:
        return "suspicious", reasons

    if positive_signals >= 3 and negative_signals == 0:
        return "verified", reasons

    # Conservative default for ambiguous or partial evidence
    if not reasons:
        reasons.append("Insufficient signals for automated verification; queued for review")
    else:
        reasons.append("Evidence requires human review")
    return "needs_review", reasons

