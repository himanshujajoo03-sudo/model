from __future__ import annotations

"""
Normalized Event Schema and Input Validation (§26, §27).
Provides a single canonical event representation to replace brittle nested .get() chains.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

try:
    from .geo import parse_and_validate_coord, classify_coordinate
    from .time_utils import parse_timestamp
except ImportError:
    from utils.geo import parse_and_validate_coord, classify_coordinate
    from utils.time_utils import parse_timestamp
except (ImportError, ValueError):
    try:
        from utils.geo import parse_and_validate_coord, classify_coordinate
        from utils.time_utils import parse_timestamp
    except (ImportError, ValueError):
        from ml.utils.geo import parse_and_validate_coord, classify_coordinate
        from ml.utils.time_utils import parse_timestamp


class EventValidationError(ValueError):
    """
    Raised when strict validation is requested (from_dict(..., strict=True))
    and one or more fields are malformed or out-of-range (as opposed to
    merely missing, which is always acceptable).
    """
    def __init__(self, message: str, issues: list[str] | None = None):
        super().__init__(message)
        self.issues = issues or []


@dataclass
class NormalizedEvent:
    """Canonical internal event representation."""
    description: str = ""
    category: Optional[str] = None
    confidence: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None
    ingestion_timestamp: Optional[datetime] = None
    city: Optional[str] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    author_id: Optional[str] = None
    event_id: Optional[str] = None
    raw: dict = field(default_factory=dict)
    # §12 hardening pass 2: records WHY a field ended up None/default, e.g.
    # "latitude_malformed" or "latitude_out_of_range", so callers can
    # distinguish "not supplied" from "supplied but invalid" when needed.
    # Always populated (in both lenient and strict mode); only strict mode
    # additionally raises on non-"missing" issues.
    validation_issues: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | Any, strict: bool = False) -> "NormalizedEvent":
        """
        Construct a NormalizedEvent from any supported dictionary schema.

        By default (strict=False, the historical/backward-compatible
        behavior), malformed or out-of-range coordinates are treated the
        same as missing ones: silently normalized to None. This preserves
        compatibility for callers that intentionally tolerate incomplete
        data (e.g. clustering, which already skips events with no usable
        coordinates).

        When strict=True, a malformed or out-of-range latitude/longitude
        raises EventValidationError instead of silently disappearing --
        for ingestion paths that should reject bad data outright rather
        than quietly treating "999" as "no coordinate given".
        """
        if isinstance(data, NormalizedEvent):
            return data

        if not isinstance(data, dict):
            return cls(raw={"value": data})

        issues: list[str] = []

        # 1. Description
        desc = (
            data.get("description")
            if data.get("description") is not None
            else (
                data.get("text")
                if data.get("text") is not None
                else (
                    data.get("event", {}).get("description")
                    if isinstance(data.get("event"), dict)
                    else data.get("event_description", "")
                )
            )
        )
        desc_str = str(desc or "").strip()

        # 2. Category
        cat = data.get("category")
        if cat is None and isinstance(data.get("event"), dict):
            cat = data["event"].get("category")
        if cat is None and isinstance(data.get("ai"), dict):
            cat = data["ai"].get("classified_category")
        if cat is None:
            cat = data.get("event_type") or data.get("label") or data.get("category_label")
        cat_str = str(cat).strip().lower() if cat is not None else None

        # 3. Confidence
        conf = data.get("confidence")
        if conf is None and isinstance(data.get("ai"), dict):
            conf = data["ai"].get("classification_confidence")
        conf_float = None
        if conf is not None:
            try:
                conf_float = float(conf)
                if conf_float != conf_float or conf_float in (float("inf"), float("-inf")):  # NaN/Inf check
                    issues.append("confidence_malformed")
                    conf_float = None
                elif not (0.0 <= conf_float <= 1.0):
                    issues.append("confidence_out_of_range")
                    conf_float = None
            except (TypeError, ValueError):
                issues.append("confidence_malformed")
                conf_float = None

        # 4. Latitude & Longitude (Explicit None checks to preserve 0.0)
        lat = data.get("latitude")
        if lat is None and isinstance(data.get("location"), dict):
            lat = data["location"].get("latitude")
        lat_status, valid_lat = classify_coordinate(lat, is_latitude=True)
        if lat_status not in ("missing", "valid"):
            issues.append(f"latitude_{lat_status}")
            valid_lat = None

        lon = data.get("longitude")
        if lon is None and isinstance(data.get("location"), dict):
            lon = data["location"].get("longitude")
        lon_status, valid_lon = classify_coordinate(lon, is_latitude=False)
        if lon_status not in ("missing", "valid"):
            issues.append(f"longitude_{lon_status}")
            valid_lon = None

        if strict and issues:
            raise EventValidationError(
                f"Event failed strict validation: {issues}. "
                "Malformed/out-of-range fields are rejected outright in strict mode "
                "(they are NOT treated as merely 'missing').",
                issues=issues,
            )

        # 5. Timestamps
        ts_val = data.get("timestamp") or data.get("event_timestamp")
        parsed_ts = parse_timestamp(ts_val)

        ing_val = data.get("ingestion_timestamp")
        parsed_ing = parse_timestamp(ing_val)

        # 6. City / Location
        city = data.get("city")
        if city is None and isinstance(data.get("location"), dict):
            city = data["location"].get("city")
        city_str = str(city).strip() if city is not None else None

        # 7. Source metadata
        source_id = data.get("source_id")
        source_url = data.get("source_url")
        source_type = data.get("source_type") or data.get("source_name")
        source_name = data.get("source_name") or data.get("source_type")

        # 8. Author metadata
        author_id = data.get("author_id")
        if author_id is None and isinstance(data.get("social_metadata"), dict):
            author_id = data["social_metadata"].get("author_id")

        event_id = data.get("event_id") or data.get("id")

        return cls(
            description=desc_str,
            category=cat_str,
            confidence=conf_float,
            latitude=valid_lat,
            longitude=valid_lon,
            timestamp=parsed_ts,
            ingestion_timestamp=parsed_ing,
            city=city_str,
            source_id=str(source_id) if source_id is not None else None,
            source_url=str(source_url) if source_url is not None else None,
            source_type=str(source_type) if source_type is not None else None,
            source_name=str(source_name) if source_name is not None else None,
            author_id=str(author_id) if author_id is not None else None,
            event_id=str(event_id) if event_id is not None else None,
            raw=data,
            validation_issues=issues,
        )

    def to_dict(self) -> dict:
        """Convert back to standard dictionary format."""
        d = dict(self.raw) if self.raw else {}
        d.update({
            "description": self.description,
            "category": self.category,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ingestion_timestamp": self.ingestion_timestamp.isoformat() if self.ingestion_timestamp else None,
            "city": self.city,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "author_id": self.author_id,
            "event_id": self.event_id,
        })
        if self.confidence is not None:
            d["confidence"] = self.confidence
        return d

    def get(self, key: str, default: Any = None) -> Any:
        """Support dictionary-style get for backward compatibility."""
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        return self.raw.get(key, default)

    def __getitem__(self, item: str) -> Any:
        """Support dictionary-style indexing."""
        val = self.get(item)
        if val is None and item not in ("confidence", "city", "event_id", "author_id"):
            if item in self.raw:
                return self.raw[item]
        return val

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item) or item in self.raw

