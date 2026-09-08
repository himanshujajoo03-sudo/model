"""API route registration contract tests."""
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]

def test_required_api_routers_are_registered():
    text = (API_ROOT / 'main.py').read_text()
    for name in ('events_router','verification_router','reports_router','system_router','health_router','auth_router','citizen_router'):
        assert f'app.include_router({name}, prefix="/api/v1")' in text
