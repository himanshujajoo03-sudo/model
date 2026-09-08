from __future__ import annotations

"""
Credibility Scoring Package.
"""

from .credibility_scorer import (
    score_credibility,
    generate_credibility_reasons,
    compute_weather_agreement,
)
from .source_weights import (
    get_source_trust,
    count_corroborations,
    DEFAULT_SOURCE_TRUST,
)

__all__ = [
    "score_credibility",
    "generate_credibility_reasons",
    "compute_weather_agreement",
    "get_source_trust",
    "count_corroborations",
    "DEFAULT_SOURCE_TRUST",
]