from __future__ import annotations

"""
Geographical calculation and boundary lookup utilities.
Robust coordinate validation, coordinate 0 handling, and haversine calculations.
"""

import json
import math
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Optional


EARTH_RADIUS_KM = 6371.0
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CITIES_FILE = CONFIG_DIR / "india_cities.json"

_CITY_BOUNDING_BOXES: Optional[dict] = None


def load_city_bounding_boxes() -> dict:
    """Load city bounding boxes configuration."""
    global _CITY_BOUNDING_BOXES
    if _CITY_BOUNDING_BOXES is not None:
        return _CITY_BOUNDING_BOXES

    if CITIES_FILE.exists():
        with open(CITIES_FILE, "r", encoding="utf-8") as f:
            _CITY_BOUNDING_BOXES = json.load(f)
    else:
        _CITY_BOUNDING_BOXES = {}

    return _CITY_BOUNDING_BOXES


def parse_and_validate_coord(val: float | str | None, is_latitude: bool = True) -> Optional[float]:
    """
    Parse and validate a latitude or longitude value.
    Returns float if valid, None if invalid or missing.
    0.0 is a valid coordinate!
    """
    status, value = classify_coordinate(val, is_latitude=is_latitude)
    return value if status == "valid" else None


def classify_coordinate(val: float | str | None, is_latitude: bool = True) -> tuple[str, Optional[float]]:
    """
    Classify a coordinate value into one of four distinct states (§12 hardening
    pass 2), instead of silently collapsing "missing" and "invalid" into the
    same None result:

      "missing"      -- val is None (acceptable: coordinate was never supplied)
      "valid"        -- val parses to a float within the valid range
      "malformed"    -- val is present but cannot be parsed as a number at all
                         (e.g. "abc"), or is NaN/Infinity
      "out_of_range" -- val parses to a number but is outside the valid
                         geographic bound (e.g. latitude=999)

    Returns (status, value) where value is the parsed float for "valid" and
    "out_of_range" (so callers can still inspect what was supplied), and None
    for "missing"/"malformed".
    """
    if val is None:
        return "missing", None

    try:
        fval = float(val)
    except (TypeError, ValueError):
        return "malformed", None

    if math.isnan(fval) or math.isinf(fval):
        return "malformed", None

    bound = 90.0 if is_latitude else 180.0
    if -bound <= fval <= bound:
        return "valid", fval
    return "out_of_range", fval


def is_valid_coordinate(lat: float | str | None, lon: float | str | None) -> bool:
    """Check whether both latitude and longitude are valid numbers within bounds."""
    c_lat = parse_and_validate_coord(lat, is_latitude=True)
    c_lon = parse_and_validate_coord(lon, is_latitude=False)
    return c_lat is not None and c_lon is not None


def haversine_km(
    lat1: float | str | None,
    lon1: float | str | None,
    lat2: float | str | None,
    lon2: float | str | None
) -> float:
    """
    Calculate the great circle distance between two points on Earth in kilometers.
    Returns float("inf") if any point has invalid/missing coordinates.
    Correctly handles (0,0), negative coordinates, and identical points.
    """
    c_lat1 = parse_and_validate_coord(lat1, is_latitude=True)
    c_lon1 = parse_and_validate_coord(lon1, is_latitude=False)
    c_lat2 = parse_and_validate_coord(lat2, is_latitude=True)
    c_lon2 = parse_and_validate_coord(lon2, is_latitude=False)

    if c_lat1 is None or c_lon1 is None or c_lat2 is None or c_lon2 is None:
        return float("inf")

    # Identical points
    if c_lat1 == c_lat2 and c_lon1 == c_lon2:
        return 0.0

    lat1_r, lon1_r = radians(c_lat1), radians(c_lon1)
    lat2_r, lon2_r = radians(c_lat2), radians(c_lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = sin(dlat / 2.0) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    c = 2.0 * atan2(sqrt(a), sqrt(max(0.0, 1.0 - a)))

    return EARTH_RADIUS_KM * c


def check_city_bounding_box(city: str | None, lat: float | None, lon: float | None) -> Optional[bool]:
    """
    Check if coordinates fall within the bounding box of the given city.
    Returns:
        True: coordinates are within the city's bounding box
        False: coordinates are outside the city's bounding box
        None: city is unknown or coordinates are missing/invalid
    """
    if not city:
        return None

    c_lat = parse_and_validate_coord(lat, is_latitude=True)
    c_lon = parse_and_validate_coord(lon, is_latitude=False)
    if c_lat is None or c_lon is None:
        return None

    boxes = load_city_bounding_boxes()
    # Case-insensitive city lookup
    city_box = None
    city_lower = str(city).strip().lower()
    for name, box in boxes.items():
        if name.lower() == city_lower:
            city_box = box
            break

    if city_box is None:
        return None

    return (
        city_box["min_lat"] <= c_lat <= city_box["max_lat"] and
        city_box["min_lon"] <= c_lon <= city_box["max_lon"]
    )

