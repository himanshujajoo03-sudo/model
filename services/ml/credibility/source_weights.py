from __future__ import annotations

"""
Source Trust and Independent Corroboration Detection.
Defined in 05_AI_ML_SPEC.md §8.3, §9.1, §9.2, §10.
Source Trust and Independent Corroboration Detection (§8.3, §9.1, §9.2, §10).
Uses symmetric category compatibility, coordinate 0 preservation, and normalized event schema.
"""

from pathlib import Path
from typing import Optional
import yaml

try:
    from ..classifier.rules import categories_are_compatible
    from ..utils.geo import haversine_km, parse_and_validate_coord
    from ..utils.time_utils import time_diff_minutes
    from ..utils.event_schema import NormalizedEvent
except ImportError:
    from classifier.rules import categories_are_compatible
    from utils.geo import haversine_km, parse_and_validate_coord
    from utils.time_utils import time_diff_minutes
    from utils.event_schema import NormalizedEvent
except (ImportError, ValueError):
    try:
        from classifier.rules import categories_are_compatible
        from utils.geo import haversine_km, parse_and_validate_coord
        from utils.time_utils import time_diff_minutes
        from utils.event_schema import NormalizedEvent
    except (ImportError, ValueError):
        from ml.classifier.rules import categories_are_compatible
        from ml.utils.geo import haversine_km, parse_and_validate_coord
        from ml.utils.time_utils import time_diff_minutes
        from ml.utils.event_schema import NormalizedEvent

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
TRUST_FILE = CONFIG_DIR / "source_trust.yaml"

# §9.1 Default Source Trust Scores
DEFAULT_SOURCE_TRUST = {
    "government_dataset": 0.95,
    "weather_api": 0.95,
    "website": 0.80,
    "rss": 0.75,
    "citizen": 0.60,
    "social": 0.55,
    "simulated_social": 0.40,
    "synthetic": 0.50,
}

_TRUST_CONFIG: Optional[dict] = None


def load_source_trust_config() -> dict:
    """Load source trust configuration from YAML (§9.2)."""
    global _TRUST_CONFIG
    if _TRUST_CONFIG is not None:
        return _TRUST_CONFIG

    if TRUST_FILE.exists():
        try:
            with open(TRUST_FILE, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                _TRUST_CONFIG = loaded or {}
        except Exception:
            _TRUST_CONFIG = {}
    else:
        _TRUST_CONFIG = {}

    return _TRUST_CONFIG


def get_source_trust(source_type: str | None, source_name: str | None = None) -> float:
    """
    Compute source trust score based on source type and specific provider overrides (§9.1, §9.2).
    """
    config = load_source_trust_config()
    trust_map = config.get("source_trust", DEFAULT_SOURCE_TRUST)
    provider_overrides = config.get("provider_overrides", {})

    # 1. Check provider override first
    if source_name and source_name in provider_overrides:
        return float(provider_overrides[source_name])

    # 2. Check source_type default
    if source_type and source_type in trust_map:
        return float(trust_map[source_type])

    # 3. Check if source_name matches a source_type key
    if source_name and source_name in trust_map:
        return float(trust_map[source_name])

    return 0.50


def count_corroborations(
    current_event: dict | NormalizedEvent,
    recent_events: list[dict | NormalizedEvent] | None = None,
    radius_km: float = 10.0,
    window_minutes: float = 30.0
) -> int:
    """
    Count independent corroborating reports (§10.1–§10.4).
    Criteria:
      1. Different source_id / source_url / author
      2. Semantically compatible categories (strictly symmetric)
      3. Spatial proximity <= radius_km (default 10 km)
      4. Temporal proximity <= window_minutes (default 30 min)
    """
    if not recent_events:
        return 0

    curr = NormalizedEvent.from_dict(current_event)
    curr_lat = curr.latitude
    curr_lon = curr.longitude
    curr_ts = curr.timestamp
    curr_cat = curr.category

    seen_source_ids = set()
    seen_source_urls = set()
    if curr.source_id:
        seen_source_ids.add(curr.source_id)
    if curr.source_url:
        seen_source_urls.add(curr.source_url)

    corroboration_count = 0

    for candidate in recent_events:
        cand = NormalizedEvent.from_dict(candidate)

        # §10.4 Deduplication of Sources
        if cand.source_id and cand.source_id in seen_source_ids:
            continue
        if cand.source_url and cand.source_url in seen_source_urls:
            continue

        # Category compatibility check (§10.3, symmetric)
        if not categories_are_compatible(curr_cat, cand.category):
            continue

        # Spatial check
        dist = haversine_km(curr_lat, curr_lon, cand.latitude, cand.longitude)
        if dist > radius_km:
            continue

        # Temporal check
        diff_min = time_diff_minutes(curr_ts, cand.timestamp)
        if diff_min > window_minutes:
            continue

        # Check author deduplication within 5 minutes
        if (
            curr.author_id and cand.author_id and
            curr.author_id == cand.author_id and
            diff_min <= 5.0
        ):
            continue

        if cand.source_id:
            seen_source_ids.add(cand.source_id)
        if cand.source_url:
            seen_source_urls.add(cand.source_url)

        corroboration_count += 1

    return corroboration_count

