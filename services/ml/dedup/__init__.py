from __future__ import annotations

"""
Duplicate Detection Package.
"""

from .duplicate_detector import (
    compute_duplicate_score,
    compute_duplicate_evidence,
    is_duplicate,
    is_review_candidate,
    DUP_WEIGHTS,
)

__all__ = [
    "compute_duplicate_score",
    "compute_duplicate_evidence",
    "is_duplicate",
    "is_review_candidate",
    "DUP_WEIGHTS",
]