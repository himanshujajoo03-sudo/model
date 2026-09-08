from __future__ import annotations

"""
Spatial-Temporal Event Clustering.
Defined in 05_AI_ML_SPEC.md §13, §14.
Sourced parameters from centralized configuration, symmetric category compatibility,
coordinate 0 preservation, and future timestamp guardrails.
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional, Any

try:
    from ..classifier.rules import categories_are_compatible
    from ..utils.geo import haversine_km, parse_and_validate_coord
    from ..utils.time_utils import parse_timestamp, time_diff_minutes, check_future_timestamp
    from ..config.config_loader import load_ml_config
    from ..utils.event_schema import NormalizedEvent
except ImportError:
    from classifier.rules import categories_are_compatible
    from utils.geo import haversine_km, parse_and_validate_coord
    from utils.time_utils import parse_timestamp, time_diff_minutes, check_future_timestamp
    from config.config_loader import load_ml_config
    from utils.event_schema import NormalizedEvent
except (ImportError, ValueError):
    try:
        from classifier.rules import categories_are_compatible
        from utils.geo import haversine_km, parse_and_validate_coord
        from utils.time_utils import parse_timestamp, time_diff_minutes, check_future_timestamp
        from config.config_loader import load_ml_config
        from utils.event_schema import NormalizedEvent
    except (ImportError, ValueError):
        from ml.classifier.rules import categories_are_compatible
        from ml.utils.geo import haversine_km, parse_and_validate_coord
        from ml.utils.time_utils import parse_timestamp, time_diff_minutes, check_future_timestamp
        from ml.config.config_loader import load_ml_config
        from ml.utils.event_schema import NormalizedEvent

# §13.3 Default Parameters (Backward Compatibility)
CLUSTER_RADIUS_KM = 3.0
CLUSTER_TIME_WINDOW_MINUTES = 30.0
CLUSTER_MAX_SIZE = 50


def get_clustering_config() -> dict:
    """Retrieve validated clustering configuration."""
    cfg = load_ml_config()
    clustering = cfg.get("clustering", {})
    return {
        "radius_km": float(clustering.get("radius_km", CLUSTER_RADIUS_KM)),
        "time_window_minutes": float(clustering.get("time_window_minutes", CLUSTER_TIME_WINDOW_MINUTES)),
        "max_cluster_size": int(clustering.get("max_cluster_size", CLUSTER_MAX_SIZE)),
        "max_future_skew_minutes": float(clustering.get("max_future_skew_minutes", 5.0)),
    }


def assign_cluster(
    event: dict | NormalizedEvent,
    active_clusters: list[dict] | None = None,
    radius_km: float | None = None,
    time_window_minutes: float | None = None,
    max_size: int | None = None,
    auto_generate_on_none: bool = False
) -> Optional[str]:
    """
    Assign event to an existing active cluster or return None (§13.4).
    When None is returned, PostgreSQL writer / caller creates a new cluster.
    """
    cfg = get_clustering_config()
    if radius_km is None:
        radius_km = cfg["radius_km"]
    if time_window_minutes is None:
        time_window_minutes = cfg["time_window_minutes"]
    if max_size is None:
        max_size = cfg["max_cluster_size"]

    if not active_clusters:
        return str(uuid4()) if auto_generate_on_none else None

    curr = NormalizedEvent.from_dict(event)

    # Missing or invalid coordinates cannot cluster
    if curr.latitude is None or curr.longitude is None:
        return str(uuid4()) if auto_generate_on_none else None

    # Disallow significantly future events from clustering with historical clusters
    is_future, skew = check_future_timestamp(curr.timestamp, allowed_skew_minutes=cfg["max_future_skew_minutes"])
    if is_future:
        return str(uuid4()) if auto_generate_on_none else None

    best_cluster_id = None
    best_score = 0.0

    for cluster in active_clusters:
        # 1. Check category compatibility (symmetric)
        cluster_cat = cluster.get("category") or cluster.get("classified_category")
        if not categories_are_compatible(curr.category, cluster_cat):
            continue

        # 2. Check spatial proximity (with coordinate 0 support)
        c_lat_raw = cluster.get("centroid_lat") if cluster.get("centroid_lat") is not None else cluster.get("latitude")
        c_lon_raw = cluster.get("centroid_lon") if cluster.get("centroid_lon") is not None else cluster.get("longitude")
        c_lat = parse_and_validate_coord(c_lat_raw, is_latitude=True)
        c_lon = parse_and_validate_coord(c_lon_raw, is_latitude=False)
        if c_lat is None or c_lon is None:
            continue

        distance = haversine_km(curr.latitude, curr.longitude, c_lat, c_lon)
        if distance > radius_km:
            continue

        # 3. Check temporal proximity
        last_event_ts = cluster.get("last_event_at") or cluster.get("timestamp")
        time_gap = time_diff_minutes(curr.timestamp, last_event_ts)
        if time_gap > time_window_minutes:
            continue

        # 4. Check cluster size limit
        member_count = int(cluster.get("member_count", 1))
        if member_count >= max_size:
            continue

        # 5. Score proximity (closer in space and time = higher score)
        proximity_score = (
            (1.0 - distance / radius_km) * 0.5 +
            (1.0 - time_gap / time_window_minutes) * 0.5
        )

        if proximity_score > best_score:
            best_score = proximity_score
            best_cluster_id = cluster.get("cluster_id") or cluster.get("id")

    if best_cluster_id:
        return str(best_cluster_id)

    return str(uuid4()) if auto_generate_on_none else None


def select_cluster_representative(cluster_events: list[dict | NormalizedEvent]) -> Optional[dict]:
    """
    Select cluster representative event (§14.1).
    Deterministic criteria:
      1. Highest credibility_score
      2. Highest source trust score (tiebreaker)
      3. Earliest event_timestamp (final tiebreaker)
      4. Deterministic event_id (final stable order)
    """
    if not cluster_events:
        return None

    def sort_key(raw_evt: dict | NormalizedEvent):
        evt = NormalizedEvent.from_dict(raw_evt)
        cred_raw = evt.get("credibility_score")
        if cred_raw is None and isinstance(evt.raw.get("ai"), dict):
            cred_raw = evt.raw["ai"].get("credibility_score")
        cred = float(cred_raw) if cred_raw is not None else 0.0

        # Explicit None check (Rule 24): a legitimate trust score of 0.0 must
        # NOT be discarded in favor of the fallback field, which `x or y`
        # would incorrectly do since 0.0 is falsy in Python.
        trust_raw = evt.get("source_trust_score")
        if trust_raw is None:
            trust_raw = evt.get("source_trust")
        trust = float(trust_raw) if trust_raw is not None else 0.0

        ts = evt.timestamp
        ts_val = ts.timestamp() if ts else float("inf")
        eid = str(evt.event_id or "")

        return (-cred, -trust, ts_val, eid)

    sorted_events = sorted(cluster_events, key=sort_key)
    first = sorted_events[0]
    return first.to_dict() if isinstance(first, NormalizedEvent) else first