from __future__ import annotations

"""
Deterministic Multi-Factor Weather Report Credibility Scorer.
Defined in 05_AI_ML_SPEC.md §8, §9, §10, §15.
Sourced weights from centralized configuration with strict validation.
"""

from pathlib import Path
import yaml
from typing import Optional, Any

try:
    from ..classifier.rules import categories_are_compatible
    from ..config.config_loader import load_ml_config
    from .source_weights import get_source_trust, count_corroborations
    from ..utils.event_schema import NormalizedEvent
    from ..utils.geo import haversine_km, check_city_bounding_box
    from ..utils.time_utils import check_future_timestamp, parse_timestamp, time_diff_minutes
    from ..utils.validation import validate_score, InvalidScoreError
except (ImportError, ValueError):
    try:
        from classifier.rules import categories_are_compatible
        from config.config_loader import load_ml_config
        from credibility.source_weights import get_source_trust, count_corroborations
        from utils.event_schema import NormalizedEvent
        from utils.geo import haversine_km, check_city_bounding_box
        from utils.time_utils import check_future_timestamp, parse_timestamp, time_diff_minutes
        from utils.validation import validate_score, InvalidScoreError
    except (ImportError, ValueError):
        from ml.classifier.rules import categories_are_compatible
        from ml.config.config_loader import load_ml_config
        from ml.credibility.source_weights import get_source_trust, count_corroborations
        from ml.utils.event_schema import NormalizedEvent
        from ml.utils.geo import haversine_km, check_city_bounding_box
        from ml.utils.time_utils import check_future_timestamp, parse_timestamp, time_diff_minutes
        from ml.utils.validation import validate_score, InvalidScoreError

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "ml_config.yaml"

# §8.2 Default Factor Weights (Backward Compatibility)
DEFAULT_CREDIBILITY_WEIGHTS = {
    "source_trust": 0.30,
    "corroboration": 0.25,
    "weather_agreement": 0.20,
    "temporal_consistency": 0.10,
    "spatial_consistency": 0.10,
    "content_quality": 0.05,
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp float to [minimum, maximum]."""
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(maximum, fval))


def get_credibility_weights() -> dict[str, float]:
    """Retrieve validated credibility weights from centralized configuration."""
    cfg = load_ml_config()
    weights = cfg.get("credibility", {}).get("weights", {})
    return {
        "source_trust": float(weights.get("source_trust", 0.30)),
        "corroboration": float(weights.get("corroboration", 0.25)),
        "weather_agreement": float(weights.get("weather_agreement", 0.20)),
        "temporal_consistency": float(weights.get("temporal_consistency", 0.10)),
        "spatial_consistency": float(weights.get("spatial_consistency", 0.10)),
        "content_quality": float(weights.get("content_quality", 0.05)),
    }


def compute_corroboration_score(corroboration_count: int) -> float:
    """Score based on number of independent corroborating reports (§8.3)."""
    if corroboration_count <= 0:
        return 0.0
    elif corroboration_count == 1:
        return 0.40
    elif corroboration_count == 2:
        return 0.70
    elif corroboration_count == 3:
        return 0.85
    else:
        return min(0.95, 0.85 + (corroboration_count - 3) * 0.03)


def compute_weather_agreement(event: NormalizedEvent, recent_events: list[NormalizedEvent] | None = None) -> float:
    """
    Check if structured weather data agrees with the reported event (§8.3).
    - If source is weather_api / Open-Meteo / IMD: full agreement (1.0).
    - If other sources: check for nearby weather_api event with compatible category.
    - If no weather API data is available: neutral score (0.30).
    """
    if event.source_type in ("weather_api", "Open-Meteo", "IMD") or event.source_name in ("weather_api", "Open-Meteo", "IMD"):
        return 1.0

    if not recent_events:
        return 0.30  # Neutral when no API data to compare

    api_events = [
        e for e in recent_events
        if (getattr(e, "source_type", None) in ("weather_api", "Open-Meteo", "IMD") or
            getattr(e, "source_name", None) in ("weather_api", "Open-Meteo", "IMD") or
            (isinstance(e, dict) and (e.get("source_type") in ("weather_api", "Open-Meteo", "IMD") or e.get("source_name") in ("weather_api", "Open-Meteo", "IMD"))))
    ]

    if not api_events:
        return 0.30

    # Agreement must refer to the same observation window, not merely a
    # nearby API record from an unrelated date.  When both timestamps exist,
    # enforce the configured corroboration window.  If either timestamp is
    # missing, spatial/category agreement is retained but cannot be treated as
    # time-confirmed evidence.
    cfg = load_ml_config()
    window_minutes = float(cfg.get("corroboration", {}).get("window_minutes", 30.0))
    for api_evt in api_events:
        api_norm = NormalizedEvent.from_dict(api_evt) if isinstance(api_evt, dict) else api_evt
        dist = haversine_km(event.latitude, event.longitude, api_norm.latitude, api_norm.longitude)
        if dist > 25.0:
            continue
        if not categories_are_compatible(event.category, api_norm.category):
            continue
        if event.timestamp is not None and api_norm.timestamp is not None:
            if time_diff_minutes(event.timestamp, api_norm.timestamp) > window_minutes:
                continue
            return 0.90
        # Missing time metadata: useful but weaker than time-confirmed API data.
        return 0.60

    return 0.20


def compute_temporal(event: NormalizedEvent) -> float:
    """Evaluate temporal consistency of report vs ingestion timestamp (§8.3)."""
    event_ts = event.timestamp
    ingestion_ts = event.ingestion_timestamp

    if not event_ts:
        return 0.50

    # Check future timestamp policy
    is_future, skew_minutes = check_future_timestamp(event_ts, reference_ts=ingestion_ts, allowed_skew_minutes=5.0)
    if is_future:
        return 0.10  # Significant penalty for future timestamps

    if not ingestion_ts:
        return 0.80  # Default reasonable if ingestion timestamp not supplied

    lag_minutes = (ingestion_ts - event_ts).total_seconds() / 60.0
    if lag_minutes < -5.0:
        return 0.10  # Future timestamp relative to ingestion
    elif lag_minutes < 0:
        return 0.80  # Slight clock skew (<= 5 min) is normal
    elif lag_minutes < 30:
        return 1.0
    elif lag_minutes < 120:
        return 0.70
    elif lag_minutes < 360:
        return 0.50
    else:
        return 0.30


def compute_spatial(event: NormalizedEvent) -> float:
    """Evaluate spatial consistency against city bounding boxes (§8.3)."""
    lat = event.latitude
    lon = event.longitude
    city = event.city

    if lat is None or lon is None:
        return 0.50
    if not city:
        return 0.70

    is_valid = check_city_bounding_box(city, lat, lon)
    if is_valid is True:
        return 1.0
    elif is_valid is False:
        return 0.30
    return 0.60


def compute_content_quality(event: NormalizedEvent) -> float:
    """Assess description specificity and length (§8.3)."""
    desc_clean = event.description.strip()
    length = len(desc_clean)

    if length == 0:
        return 0.20
    elif length < 20:
        return 0.30
    elif length < 100:
        return 0.70
    else:
        return 0.90


def generate_credibility_reasons(factors: dict, event: NormalizedEvent, corroboration_count: int = 0) -> list[str]:
    """Generate deterministic, human-readable credibility reasons (§15.2)."""
    reasons = []

    # 1. Source trust
    trust = factors.get("source_trust", 0.50)
    if trust >= 0.80:
        reasons.append("Source has high configured trust score")
    elif trust >= 0.60:
        reasons.append("Source has moderate configured trust score")
    else:
        reasons.append("Source has low configured trust score")

    # 2. Corroboration
    if corroboration_count >= 2:
        reasons.append(f"{corroboration_count + 1} independent reports detected within proximity")
    elif corroboration_count == 1:
        reasons.append("1 additional corroborating report detected")
    else:
        reasons.append("No independent corroborating reports detected")

    # 3. Weather agreement
    weather = factors.get("weather_agreement", 0.50)
    if weather >= 0.80:
        reasons.append("Structured weather observations are consistent with the report")
    elif weather <= 0.30:
        reasons.append("No corroborating weather observation data found")

    # 4. Temporal consistency
    temporal = factors.get("temporal_consistency", 0.50)
    if temporal >= 0.80:
        reasons.append("Report timestamp is consistent with event occurrence")
    elif temporal <= 0.20:
        reasons.append("Report timestamp is in the future and flagged as suspicious")
    elif temporal <= 0.30:
        reasons.append("Report timestamp shows significant delay from event occurrence")

    # 5. Spatial consistency
    spatial = factors.get("spatial_consistency", 0.50)
    if spatial >= 0.80:
        reasons.append("Reported coordinates are consistent with stated location")
    elif spatial <= 0.30:
        reasons.append("Reported coordinates do not align with stated location")

    # 6. Content quality
    quality = factors.get("content_quality", 0.50)
    if quality >= 0.70:
        reasons.append("Report contains detailed descriptive content")
    elif quality <= 0.40:
        reasons.append("Report description is minimal or absent")

    return reasons


def score_credibility(
    event: dict | NormalizedEvent | None = None,
    recent_events: list[dict | NormalizedEvent] | None = None,
    **kwargs: Any
) -> dict:
    """
    Compute credibility score and reasons (§8.1).
    Supports NormalizedEvent, raw dict, or legacy keyword arguments.

    Returns:
        {
            "credibility_score": float,
            "credibility_reasons": list[str],
            "reasons": list[str],
            "factors": dict
        }
    """
    # Normalize legacy and integration-facing aliases to one canonical vocabulary.
    if event is None:
        event = kwargs
    raw_event = event if isinstance(event, dict) else None
    norm_event = NormalizedEvent.from_dict(event)
    norm_recent = [NormalizedEvent.from_dict(e) for e in recent_events] if recent_events else []

    # A supplied-but-malformed timestamp is suspicious and must not be treated
    # the same as a genuinely missing timestamp.
    malformed_timestamp = False
    if raw_event is not None and raw_event.get("timestamp") not in (None, ""):
        malformed_timestamp = parse_timestamp(raw_event.get("timestamp")) is None

    corrob_cnt = count_corroborations(norm_event, norm_recent)

    def _override(canonical: str, aliases: tuple[str, ...], default):
        supplied=[name for name in (canonical, *aliases) if name in kwargs]
        if not supplied: return default
        if len(supplied)>1 and any(kwargs[name] != kwargs[supplied[0]] for name in supplied[1:]):
            raise ValueError(f"Conflicting credibility overrides supplied for {canonical}: {supplied}")
        return validate_score(kwargs[supplied[0]], canonical, allow_none=False)

    corrob_factor = _override("corroboration", ("cross_source_agreement",), compute_corroboration_score(corrob_cnt))

    factors = {
        "source_trust": get_source_trust(norm_event.source_type, norm_event.source_name),
        "corroboration": corrob_factor,
        "weather_agreement": (
            _override("weather_agreement", ("weather_confirmation",), compute_weather_agreement(norm_event, norm_recent))
        ),
        "temporal_consistency": (
            _override("temporal_consistency", ("timestamp_validity",), 0.10 if malformed_timestamp else compute_temporal(norm_event))
        ),
        "spatial_consistency": (
            _override("spatial_consistency", ("location_validity",), compute_spatial(norm_event))
        ),
        "content_quality": (
            _override("content_quality", ("completeness",), compute_content_quality(norm_event))
        ),
    }

    weights = get_credibility_weights()
    score = sum(factors[k] * weights[k] for k in factors)
    final_score = round(clamp(score), 3)

    reasons = generate_credibility_reasons(factors, norm_event, corrob_cnt)

    return {
        "credibility_score": final_score,
        "credibility_reasons": reasons,
        "reasons": reasons,
        "factors": factors,
    }