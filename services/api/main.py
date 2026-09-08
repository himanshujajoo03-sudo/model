"""
SIH26069 — FastAPI Backend
REST API for the weather intelligence platform.

This is a skeleton entrypoint. Endpoints per 04_API_CONTRACT.md.
"""

from fastapi import FastAPI
import asyncio
from api.services.verification_outbox import publish_pending
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="SIH26069 — National Weather Big Data Analytics Platform",
    docs_url="/docs",
    redoc_url="/redoc",
)


async def _verification_outbox_worker():
    while True:
        try:
            await asyncio.to_thread(publish_pending)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Verification outbox worker failed: %s", exc)
        await asyncio.sleep(5)


@app.on_event("startup")
async def start_background_workers():
    app.state.verification_outbox_task = asyncio.create_task(_verification_outbox_worker())


@app.on_event("shutdown")
async def stop_background_workers():
    task = getattr(app.state, "verification_outbox_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

# CORS — allow both the Vite dev server (5173) and the Docker-mapped
# frontend (3000) by default; override via CORS_ORIGINS (comma-separated).
cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.events import router as events_router
from routers.verification import router as verification_router
from routers.reports import router as reports_router
from routers.system import router as system_router
from routers.health import router as health_router
from routers.auth import router as auth_router
from routers.citizen import router as citizen_router

app.include_router(events_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(citizen_router, prefix="/api/v1")

# Serve uploaded citizen media without bypassing the API/Kafka event path.
_media_path = os.environ.get("MEDIA_UPLOAD_PATH", "/data/media")
os.makedirs(_media_path, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_path), name="media")
