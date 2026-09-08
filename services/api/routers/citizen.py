"""Citizen report endpoint — POST /api/v1/citizen-reports."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.services.citizen_service import submit_report
from ingestion.adapters.citizen import normalize_citizen_report

router = APIRouter(tags=["citizen"])
VALID_CATEGORIES = {"rainfall", "heavy_rainfall", "flood", "thunderstorm", "lightning", "heatwave", "fog", "dust_storm", "strong_wind", "hailstorm", "cyclone", "other"}
VALID_SEVERITIES = {"low", "moderate", "high", "extreme"}
MAX_PHOTOS, MAX_VIDEOS = 5, 2
MAX_PHOTO_BYTES, MAX_VIDEO_BYTES = 5 * 1024 * 1024, 20 * 1024 * 1024


def _parse_timestamp(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid ISO 8601 timestamp") from exc
    if (dt - datetime.now(timezone.utc)).total_seconds() > 300:
        raise HTTPException(status_code=422, detail="timestamp cannot be more than 5 minutes in the future")
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def _save_files(files: list[UploadFile], kind: str, limit: int, max_bytes: int) -> list[str]:
    if len(files) > limit:
        raise HTTPException(status_code=413, detail=f"Maximum {limit} {kind} files allowed")
    subdir = "photos" if kind == "photos" else "videos"
    base = Path(os.environ.get("MEDIA_UPLOAD_PATH", "/data/media")) / subdir
    base.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    for upload in files:
        data = await upload.read()
        if len(data) > max_bytes:
            raise HTTPException(status_code=413, detail=f"{kind} file exceeds size limit")
        suffix = Path(upload.filename or "").suffix.lower() or ".bin"
        name = f"{uuid.uuid4()}{suffix}"
        (base / name).write_bytes(data)
        urls.append(f"/media/{subdir}/{name}")
    return urls


@router.post("/citizen-reports", status_code=201)
async def submit_citizen_report(
    city: str = Form(...), district: str | None = Form(None), state: str | None = Form(None),
    latitude: float | None = Form(None), longitude: float | None = Form(None),
    category: str = Form(...), severity: str | None = Form(None), description: str | None = Form(None),
    timestamp: str | None = Form(None), photos: list[UploadFile] = File(default=[]), videos: list[UploadFile] = File(default=[]),
):
    city = city.strip()
    category = category.strip().lower()
    if not city:
        raise HTTPException(status_code=422, detail="city is required")
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid category")
    if severity is not None:
        severity = severity.strip().lower()
        if severity not in VALID_SEVERITIES:
            raise HTTPException(status_code=422, detail="Invalid severity")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="latitude and longitude must be supplied together")
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(status_code=422, detail="latitude out of range")
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="longitude out of range")
    if description and len(description) > 2000:
        raise HTTPException(status_code=422, detail="description exceeds 2000 characters")

    photo_urls = await _save_files(photos, "photos", MAX_PHOTOS, MAX_PHOTO_BYTES)
    video_urls = await _save_files(videos, "videos", MAX_VIDEOS, MAX_VIDEO_BYTES)
    event_timestamp = _parse_timestamp(timestamp)
    event = normalize_citizen_report(
        city=city, district=district, state=state, latitude=latitude, longitude=longitude,
        category=category, severity=severity, description=description, timestamp=event_timestamp,
        photo_urls=photo_urls, video_urls=video_urls,
    )
    try:
        submit_report(event)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Kafka unavailable: {type(exc).__name__}") from exc
    return {"event_id": event["event_id"], "status": "submitted", "message": "Citizen report submitted successfully", "timestamp": event_timestamp}
