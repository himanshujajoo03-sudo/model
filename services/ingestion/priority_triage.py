"""
SIH26069 — Fast-Path Priority Triage
Lightweight, pure-Python pre-filter to detect high-severity weather events (<5ms).
"""

from __future__ import annotations

CRITICAL_SEVERITIES = frozenset({"high", "extreme"})
CRITICAL_KEYWORDS = (
    "flood",
    "cyclone",
    "collapse",
    "trapped",
    "drowning",
    "emergency",
    "sos",
)


def is_critical(event: dict | None) -> bool:
    """
    Check if a weather event qualifies for the fast-path critical lane.

    Checks:
    1. Severity is 'high' or 'extreme'
    2. Text contains any critical keyword: flood, cyclone, collapse, trapped, drowning, emergency, sos

    Must run in < 5ms: zero network calls, zero ML, pure string/dict operations.
    """
    if not isinstance(event, dict):
        return False

    ev = event.get("event") if isinstance(event.get("event"), dict) else {}

    # 1. Severity check (case-insensitive)
    severity = str(ev.get("severity") or event.get("severity") or "").lower().strip()
    if severity in CRITICAL_SEVERITIES:
        return True

    # 2. Keyword check across description, text, and category
    text_content = " ".join([
        str(ev.get("description") or ""),
        str(event.get("description") or ""),
        str(event.get("text") or ""),
        str(ev.get("category") or ""),
        str(event.get("category") or ""),
    ]).lower()

    if any(keyword in text_content for keyword in CRITICAL_KEYWORDS):
        return True

    return False
