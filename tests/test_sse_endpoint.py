"""
SIH26069 — Server-Sent Events (SSE) Unit & Integration Tests
Validates the /api/v1/events/stream generator and SSE format.
"""

from __future__ import annotations

import sys
import uuid
import json
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "routers"))

class MockStreamingResponse:
    def __init__(self, content, media_type=None, headers=None):
        self.body_iterator = content
        self.media_type = media_type
        self.headers = headers or {}

recorded_routes = []
def mock_route_decorator(*args, **kwargs):
    if args:
        recorded_routes.append(args[0])
    def wrapper(fn):
        return fn
    return wrapper

fastapi_mock = MagicMock()
router_mock = MagicMock()
router_mock.get.side_effect = mock_route_decorator
fastapi_mock.APIRouter.return_value = router_mock

fastapi_responses_mock = MagicMock()
fastapi_responses_mock.StreamingResponse = MockStreamingResponse

sys.modules["fastapi"] = fastapi_mock
sys.modules["fastapi.responses"] = fastapi_responses_mock
sys.modules["dependencies"] = MagicMock()

# Reload or import module
if "routers.events" in sys.modules:
    del sys.modules["routers.events"]

import routers.events as events_module


def test_sse_endpoint_registration():
    assert "/events/stream" in recorded_routes, f"Route /events/stream not in registered routes: {recorded_routes}"
    assert callable(events_module.stream_events)
    print("\n[TEST PASSED] Route /events/stream registered on events router")


def test_sse_generator_output_format():
    test_id = str(uuid.uuid4())
    mock_row = (
        test_id, "flood", "extreme", "Flash flood in Mumbai",
        "Mumbai", "Maharashtra", "India", "Mumbai City",
        19.0760, 72.8777,
        "flood", 0.95, 0.88,
        "verified", ["IMD Alert"], None,
        2, 5,
        "2026-09-10T12:00:00Z", "2026-09-10T12:01:00Z", "2026-09-10T12:01:00Z",
        "2026-09-10T12:00:30Z", "2026-09-10T12:00:32Z"
    )

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # First call returns mock_row, second returns [] to test ping
    mock_cur.fetchall.side_effect = [[mock_row], []]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    events_module.get_db = MagicMock(return_value=mock_conn)
    mock_conn.__enter__.return_value = mock_conn

    # Simulate Request
    mock_request = MagicMock()
    # Disconnect after 2 loop iterations
    mock_request.is_disconnected = AsyncMock(side_effect=[False, False, True])

    async def run_test():
        response = await events_module.stream_events(mock_request)
        generator = response.body_iterator
        chunks = []
        async for chunk in generator:
            chunks.append(chunk)
            if len(chunks) >= 2:
                break
        return chunks

    chunks = asyncio.run(run_test())
    assert len(chunks) >= 2
    assert chunks[0].startswith("data: ")
    assert chunks[0].endswith("\n\n")

    payload = json.loads(chunks[0][len("data: "):-2])
    assert payload["event_id"] == test_id
    assert payload["event_category"] == "flood"
    assert payload["severity"] == "extreme"
    assert payload["city"] == "Mumbai"
    assert chunks[1] == ": ping\n\n"

    print("[TEST PASSED] SSE stream successfully yields valid 'data: {json}\\n\\n' and ': ping\\n\\n'")


def test_frontend_store_has_sse():
    store_path = REPO_ROOT / "services" / "frontend" / "src" / "stores" / "liveEventsStore.js"
    content = store_path.read_text(encoding="utf-8")
    assert "connectSse" in content
    assert "disconnectSse" in content
    assert "isLiveStreaming" in content
    assert "EventSource" in content
    assert "/events/stream" in content
    print("[TEST PASSED] liveEventsStore.js contains EventSource connection logic")


def test_frontend_ui_has_badge():
    ui_path = REPO_ROOT / "services" / "frontend" / "src" / "pages" / "LiveEvents.jsx"
    content = ui_path.read_text(encoding="utf-8")
    assert "isLiveStreaming" in content
    assert "LIVE SSE" in content
    assert "animate-ping" in content
    print("[TEST PASSED] LiveEvents.jsx contains pulsing LIVE SSE badge")


if __name__ == "__main__":
    test_sse_endpoint_registration()
    test_sse_generator_output_format()
    test_frontend_store_has_sse()
    test_frontend_ui_has_badge()
    print("\nALL SSE ENDPOINT TESTS PASSED SUCCESSFULLY!")
