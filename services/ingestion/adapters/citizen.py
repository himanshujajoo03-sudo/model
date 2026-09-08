"""Citizen source adapter: convert submitted form data into a canonical event."""
from datetime import datetime, timezone
import uuid
try:
    from ..normaliser.canonical_event import build_canonical_event
except ImportError:  # Docker/runtime compatibility when services/ingestion is PYTHONPATH root
    from normaliser.canonical_event import build_canonical_event

def normalize_citizen_report(*, city, district, state, latitude, longitude, category, severity, description, timestamp, photo_urls=None, video_urls=None):
    event = build_canonical_event(
        source_type="citizen", source_name="citizen_form", source_id=f"citizen_{uuid.uuid4()}",
        description=description, category=category,
        location={"latitude": latitude, "longitude": longitude, "city": city.strip(), "district": district, "state": state, "country": "India"},
        timestamp=timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), severity=severity,
    )
    event["media"] = {"photos": photo_urls or [], "videos": video_urls or []}
    return event
