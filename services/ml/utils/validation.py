from __future__ import annotations

"""
Common Score Validation Utilities (hardening pass 2, Rules 13 & 14).

Policy: externally supplied score-like values (credibility factor overrides
passed as keyword arguments, duplicate-score components, etc.) are REJECTED
-- not silently clamped -- when they are NaN, +/-Infinity, non-numeric, or
outside the valid [0, 1] range. Rejecting bad external input surfaces
integration bugs immediately instead of quietly corrupting scores downstream.

Internally computed scores (the result of our own arithmetic) continue to be
defensively clamped as a last resort via `clamp_score`, since those values
are trusted to be "morally" in-range and clamping only guards against
floating-point edge cases (e.g. 1.0000000000000002).
"""

import math
from typing import Optional


class InvalidScoreError(ValueError):
    """Raised when an externally supplied score is malformed: non-numeric,
    NaN, infinite, or outside the [0, 1] range."""
    pass


def validate_score(value, name: str, allow_none: bool = True) -> Optional[float]:
    """
    Validate an externally supplied score-like value.

    Returns a validated float in [0, 1], or None if value is None and
    allow_none is True.

    Raises InvalidScoreError for None (when not allowed), non-numeric types,
    NaN, +/-Infinity, or values outside [0, 1].
    """
    if value is None:
        if allow_none:
            return None
        raise InvalidScoreError(f"'{name}' must not be None.")

    if isinstance(value, bool):
        # bool is a subclass of int in Python; reject explicitly to avoid
        # True/False silently being treated as 1.0/0.0 from untyped callers.
        raise InvalidScoreError(f"'{name}' must be numeric, got bool {value!r}.")

    try:
        fval = float(value)
    except (TypeError, ValueError):
        raise InvalidScoreError(f"'{name}' must be numeric, got {value!r}.")

    if math.isnan(fval) or math.isinf(fval):
        raise InvalidScoreError(f"'{name}' must be a finite number, got {value!r}.")

    if not (0.0 <= fval <= 1.0):
        raise InvalidScoreError(f"'{name}' must be within [0, 1], got {fval}.")

    return fval


def clamp_score(value, default: float = 0.0) -> float:
    """
    Defensive last-resort clamp for internally computed scores.
    Never raises; falls back to `default` for non-numeric/NaN/Infinity input.
    """
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(fval) or math.isinf(fval):
        return default
    return max(0.0, min(1.0, fval))
