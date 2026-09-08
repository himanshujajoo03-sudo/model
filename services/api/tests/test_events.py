"""Events API route contract tests without a database dependency."""
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]

def test_events_routes_are_declared():
    text = (API_ROOT / 'routers/events.py').read_text()
    assert '@router.get("/events"' in text
    assert '@router.get("/events/stats"' in text
    assert '@router.get("/events/map"' in text
