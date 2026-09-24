"""
Canonical Weather Event builder.
Transforms raw source data into the Canonical Weather Event structure
defined in 02_DATA_SCHEMA.md §2.

Weather code mapping per 06_IMPLEMENTATION_PLAN.md §11 Open-Meteo adapter spec.
"""

import uuid
import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ingestion.normaliser")


# ── Open-Meteo WMO Weather Code → Event Category ───────────────────
# Only maps codes that represent a meaningful weather event.
# Returns None for benign conditions (clear sky, partly cloudy, etc.)
# Source: 06_IMPLEMENTATION_PLAN.md §11, 05_AI_ML_SPEC.md §10
WMO_CODE_TO_CATEGORY = {
    # Fog
    45: "fog",
    48: "fog",
    # Heavy rainfall / freezing rain
    65: "heavy_rainfall",
    66: "heavy_rainfall",
    67: "heavy_rainfall",
    # Thunderstorm (with or without hail)
    95: "thunderstorm",
    96: "thunderstorm",
    99: "thunderstorm",
}

# Weather codes that are potentially severe depending on measurements.
# These are NOT inherently severe — severity is derived from actual values.
CONDITIONAL_CODES = {
    # Rainfall
    51, 53, 55, 56, 57, 61, 63,
    # Rain showers
    80, 81, 82,
}

# Snow-related WMO codes — NOT in the canonical taxonomy.
# These are skipped (not misclassified as fog or any other category).
SNOW_CODES = {71, 73, 75, 77, 85, 86}

# Codes that are benign and should be skipped entirely.
BENIGN_CODES = {0, 1, 2, 3}


def build_canonical_event(
    source_type,
    source_name,
    source_id,
    description,
    category,
    location,
    timestamp,
    source_url=None,
    severity=None,
    hashtags=None,
):
    """Build a Canonical Weather Event matching 02_DATA_SCHEMA.md §2.

    event_id is deterministic: hash(source_type + source_id + timestamp + lat + lon).
    This ensures the same source observation always produces the same event_id,
    making reprocessing idempotent via ON CONFLICT (event_id) DO UPDATE.
    """
    # Deterministic event_id from stable source fields
    loc = location or {}
    if source_type == "synthetic":
        hash_input = source_id
    else:
        hash_input = f"{source_type}|{source_id}|{timestamp}|{loc.get('latitude', '')}|{loc.get('longitude', '')}"
    raw = bytearray(hashlib.sha256(hash_input.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40  # version 4
    raw[8] = (raw[8] & 0x3F) | 0x80  # RFC 4122 variant
    deterministic_id = str(uuid.UUID(bytes=bytes(raw)))

    return {
        "event_id": deterministic_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_name": source_name,
        "source_url": source_url,
        "source_trust_score": None,
        "timestamp": timestamp,
        "ingestion_timestamp": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        ),
        "location": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "city": location.get("city"),
            "district": location.get("district"),
            "state": location.get("state"),
            "country": location.get("country", "India"),
        },
        "event": {
            "category": category,
            "severity": severity,
            "description": description,
        },
        "social_metadata": {
            "hashtags": hashtags or [],
            "author_id": None,
            "platform": None,
        },
        "media": {"photos": [], "videos": []},
        "ai": {
            "classified_category": None,
            "classification_confidence": None,
            "duplicate_score": None,
            "credibility_score": None,
            "credibility_reasons": [],
            "cluster_id": None,
        },
        "verification": {
            "status": "pending",
            "verified_by": None,
            "verification_timestamp": None,
        },
    }


def derive_event_category(weather_code, temperature_c=None, wind_speed_kmh=None, precipitation_mm=None):
    """
    Map an Open-Meteo WMO weather code + measurements to a canonical event category.

    Returns (category: str | None, severity: str | None).
    Returns (None, None) if the observation does not represent a meaningful weather event.

    Evaluation order (designed to prevent misclassification):
        1. Snow codes → always skip (not in canonical taxonomy)
        2. Definitive WMO codes (fog 45/48, heavy rain 65-67, thunderstorm 95-99)
           → map directly regardless of measurements
        3. Measurement-based detection (heatwave, strong_wind, heavy_rainfall)
           → only for codes NOT already handled by step 2
        4. Benign codes (0-3) → skip
        5. Conditional codes (rain) → only if precipitation significant

    Severity thresholds (derived from 05_AI_ML_SPEC.md §10):
        - temperature_c >= 42  → heatwave (extreme)
        - temperature_c >= 40  → heatwave (high)
        - precipitation_mm > 50 → heavy_rainfall (extreme)
        - precipitation_mm > 20 → heavy_rainfall (high)
        - precipitation_mm > 7.5 → heavy_rainfall (moderate)
        - wind_speed_kmh > 90 → strong_wind (extreme)
        - wind_speed_kmh > 62 → strong_wind (high)
        - wind_speed_kmh > 50 → strong_wind (moderate)
    """
    # ── Step 1: Snow codes → unsupported, always skip ────────────────
    if weather_code in SNOW_CODES:
        logger.info(
            "Unsupported snow weather code %d; skipping observation",
            weather_code,
        )
        return None, None

    # ── Step 2: Definitive WMO codes → map directly ──────────────────
    # These codes unambiguously identify a weather event regardless of
    # temperature/wind/precipitation measurements.
    if weather_code in WMO_CODE_TO_CATEGORY:
        category = WMO_CODE_TO_CATEGORY[weather_code]
        severity = _derive_severity(category, temperature_c, wind_speed_kmh, precipitation_mm)
        return category, severity

    # ── Step 3: Measurement-based detection ───────────────────────────
    # For codes NOT in WMO_CODE_TO_CATEGORY (benign, conditional, unknown),
    # derive events from actual measurements.

    # Heatwave detection from temperature
    if temperature_c is not None and temperature_c >= 40:
        severity = "extreme" if temperature_c >= 42 else "high"
        return "heatwave", severity

    # Strong wind from wind speed measurement
    if wind_speed_kmh is not None and wind_speed_kmh >= 50:
        if wind_speed_kmh >= 90:
            severity = "extreme"
        elif wind_speed_kmh >= 62:
            severity = "high"
        else:
            severity = "moderate"
        return "strong_wind", severity

    # Heavy rainfall from precipitation measurement
    if precipitation_mm is not None and precipitation_mm > 7.5:
        if precipitation_mm > 50:
            severity = "extreme"
        elif precipitation_mm > 20:
            severity = "high"
        else:
            severity = "moderate"
        return "heavy_rainfall", severity

    # ── Step 4: Benign codes → skip ──────────────────────────────────
    if weather_code is None or weather_code in BENIGN_CODES:
        return None, None

    # ── Step 5: Conditional codes (rain) → only if precip significant ─
    if weather_code in CONDITIONAL_CODES:
        if precipitation_mm is not None and precipitation_mm > 2.5:
            if weather_code in (80, 81, 82, 61, 63):
                cat = "heavy_rainfall" if weather_code in (81, 82, 63) else "rainfall"
                sev = "high" if precipitation_mm > 10 else "moderate"
                return cat, sev
            elif weather_code in (51, 53, 55, 56, 57):
                return "rainfall", "moderate"

    # Unknown or benign code with no measurement thresholds → skip
    return None, None


def _derive_severity(category, temperature_c, wind_speed_kmh, precipitation_mm):
    """Derive severity from category + actual measurements."""
    if category == "heatwave":
        if temperature_c is not None:
            if temperature_c >= 42:
                return "extreme"
            elif temperature_c >= 40:
                return "high"
            else:
                return "moderate"
        return "moderate"

    if category == "heavy_rainfall":
        if precipitation_mm is not None:
            if precipitation_mm > 50:
                return "extreme"
            elif precipitation_mm > 20:
                return "high"
            else:
                return "moderate"
        return "moderate"

    if category == "strong_wind":
        if wind_speed_kmh is not None:
            if wind_speed_kmh >= 90:
                return "extreme"
            elif wind_speed_kmh >= 62:
                return "high"
            else:
                return "moderate"
        return "moderate"

    # Default for thunderstorm, fog, etc.
    return "moderate"
