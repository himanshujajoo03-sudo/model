from __future__ import annotations

"""
Verification Decision Engine Package.
"""

try:
    from .verification_engine import decide_verification
except (ImportError, ValueError):
    try:
        from verification_engine import decide_verification
    except (ImportError, ValueError):
        from ml.verification.verification_engine import decide_verification

__all__ = ["decide_verification"]
