"""Citizen API contract tests without requiring external services."""
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]

def test_citizen_router_is_registered():
    text = (API_ROOT / 'main.py').read_text()
    assert 'from routers.citizen import router as citizen_router' in text
    assert 'app.include_router(citizen_router, prefix="/api/v1")' in text

def test_citizen_route_has_no_stale_variables():
    text = (API_ROOT / 'routers/citizen.py').read_text()
    assert 'event_timestamp=event_timestamp' not in text
    assert 'photo_urls=photo_urls' in text
    assert 'video_urls=video_urls' in text
    assert 'return {"event_id": event["event_id"]' in text
