from __future__ import annotations

"""
Timestamp parsing and time difference utilities.
Standardizes on timezone-aware UTC datetime and handles clock skew/future timestamps.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def parse_timestamp(value: str | datetime | None) -> Optional[datetime]:
    """
    Parse an ISO-8601 or string timestamp into a timezone-aware UTC datetime.
    Converts naive datetimes to UTC.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    val_str = str(value).strip()
    if not val_str:
        return None

    # Replace 'Z' with '+00:00' for standard fromisoformat compatibility
    val_str = val_str.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        # Fall through to explicitly supported legacy formats. Invalid values
        # remain None; callers can distinguish malformed from missing input.
        pass

    # Try common fallback patterns
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def time_diff_minutes(ts1: str | datetime | None, ts2: str | datetime | None) -> float:
    """
    Calculate absolute difference in minutes between two timestamps.
    Both timestamps are normalized to UTC.
    Returns infinity if either timestamp cannot be parsed.
    """
    dt1 = parse_timestamp(ts1)
    dt2 = parse_timestamp(ts2)

    if dt1 is None or dt2 is None:
        return float("inf")

    return abs((dt1 - dt2).total_seconds()) / 60.0


def check_future_timestamp(
    event_ts: str | datetime | None,
    reference_ts: str | datetime | None = None,
    allowed_skew_minutes: float = 5.0
) -> tuple[bool, float]:
    """
    Check if an event timestamp is in the future relative to reference (or now in UTC).
    Returns (is_future, skew_minutes).
    skew_minutes > 0 indicates future event.
    """
    e_dt = parse_timestamp(event_ts)
    if e_dt is None:
        return False, 0.0

    r_dt = parse_timestamp(reference_ts) if reference_ts else datetime.now(timezone.utc)
    if r_dt is None:
        r_dt = datetime.now(timezone.utc)

    diff_seconds = (e_dt - r_dt).total_seconds()
    skew_minutes = diff_seconds / 60.0

    is_future = skew_minutes > allowed_skew_minutes
    return is_future, max(0.0, skew_minutes)
