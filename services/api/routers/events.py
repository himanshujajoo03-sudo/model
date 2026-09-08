"""
Events router — GET /events, /events/stats, /events/map, /events/{id}
Queries canonical_events table (consolidated weather phenomena).

IMPORTANT: /stats and /map routes MUST be defined before /{event_id}
to prevent FastAPI from matching "stats" / "map" as a path parameter.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from dependencies import get_db

router = APIRouter(tags=["events"])


# ═══════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════


class EventListItem(BaseModel):
    event_id: str
    source_type: str = "canonical"
    source_name: str = "aggregated"
    event_timestamp: str
    event_category: str
    severity: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    classified_category: Optional[str] = None
    classification_confidence: Optional[float] = None
    credibility_score: Optional[float] = None
    duplicate_score: Optional[float] = None
    verification_status: str = "pending"
    verification_reasons: list[str] = []
    cluster_id: Optional[str] = None
    source_count: int = 1
    report_count: int = 1
    created_at: str


class EventListResponse(BaseModel):
    items: list[EventListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class EventDetailSource(BaseModel):
    source_id: str = "canonical"
    source_type: str = "aggregated"
    source_name: str = "aggregated"
    source_url: Optional[str] = None
    source_trust_score: Optional[float] = None


class EventDetailLocation(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"


class EventDetailEvent(BaseModel):
    category: str
    severity: Optional[str] = None
    description: Optional[str] = None


class EventDetailSocialMetadata(BaseModel):
    hashtags: list[str] = []
    author_id: Optional[str] = None
    platform: Optional[str] = None


class EventDetailMedia(BaseModel):
    photo_urls: list[str] = []
    video_urls: list[str] = []


class EventDetailAI(BaseModel):
    classified_category: Optional[str] = None
    classification_confidence: Optional[float] = None
    duplicate_score: Optional[float] = None
    credibility_score: Optional[float] = None
    credibility_reasons: list[str] = []
    cluster_id: Optional[str] = None


class EventDetailVerification(BaseModel):
    status: str = "pending"
    verified_by: Optional[str] = None
    verification_timestamp: Optional[str] = None
    verification_reasons: list[str] = []
    history: list[dict] = []


class EventDetailResponse(BaseModel):
    event_id: str
    source: EventDetailSource
    event_timestamp: str
    ingestion_timestamp: str
    location: EventDetailLocation
    event: EventDetailEvent
    social_metadata: EventDetailSocialMetadata
    media: EventDetailMedia
    ai: EventDetailAI
    verification: EventDetailVerification
    source_count: int = 1
    report_count: int = 1
    created_at: str
    updated_at: str


class StatsResponse(BaseModel):
    total_events: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_city: dict[str, int]
    by_verification_status: dict[str, int]
    by_source_type: dict[str, int]
    average_credibility_score: Optional[float] = None
    events_over_time: list[dict]


class MapEvent(BaseModel):
    event_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_category: str
    severity: Optional[str] = None
    city: Optional[str] = None
    credibility_score: Optional[float] = None
    verification_status: str
    event_timestamp: str


class MapResponse(BaseModel):
    events: list[MapEvent]
    count: int
    bbox: dict


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _dt_to_iso(dt) -> str | None:
    """Convert a datetime/timestamptz to ISO 8601 UTC string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _error(code: str, message: str, status_code: int):
    """Raise HTTPException with the standard error response format."""
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": None,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            }
        },
    )


def _fetch_ce_distribution(where: str, params: list, col: str) -> dict[str, int]:
    """Fetch count distribution for a given column from canonical_events."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {col}, COUNT(*) FROM canonical_events "
                f"WHERE {where} AND {col} IS NOT NULL "
                f"GROUP BY {col} ORDER BY COUNT(*) DESC",
                params,
            )
            return {row[0]: row[1] for row in cur.fetchall()}


# ═══════════════════════════════════════════════════════════════════
# Routes — ordered: /stats, /map before /{event_id}
# ═══════════════════════════════════════════════════════════════════


# ── GET /events ────────────────────────────────────────────────────


@router.get("/events", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    city: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    min_credibility: Optional[float] = Query(None, ge=0.0, le=1.0),
    sort_by: str = Query("last_seen"),
    sort_order: str = Query("desc"),
):
    """List canonical weather events with pagination."""
    # The frontend requests event_timestamp (canonical events have no such column;
    # the closest equivalent is last_seen). Map it explicitly so the sort UI works.
    SORT_ALIASES = {"event_timestamp": "last_seen"}
    sort_by = SORT_ALIASES.get(sort_by, sort_by)
    allowed_sort = {
        "last_seen", "first_seen", "created_at", "credibility_score",
        "event_category", "severity", "city", "source_count", "report_count",
        "classification_confidence",
    }
    if sort_by not in allowed_sort:
        sort_by = "last_seen"
    sort_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

    conditions: list[str] = []
    params: list = []

    if city:
        conditions.append("city = %s"); params.append(city)
    if district:
        conditions.append("district = %s"); params.append(district)
    if state:
        conditions.append("state = %s"); params.append(state)
    if category:
        conditions.append("event_category = %s"); params.append(category)
    if severity:
        conditions.append("severity = %s"); params.append(severity)
    if verification_status:
        conditions.append("verification_status = %s"); params.append(verification_status)
    if source_type:
        # source_type filter: check if the canonical event has records from this source type
        conditions.append(
            "canonical_event_id IN (SELECT canonical_event_id FROM events WHERE source_type = %s)"
        ); params.append(source_type)
    if start_time:
        conditions.append("last_seen >= %s"); params.append(start_time)
    if end_time:
        conditions.append("last_seen <= %s"); params.append(end_time)
    if min_credibility is not None:
        conditions.append("credibility_score >= %s"); params.append(min_credibility)

    where = " AND ".join(conditions) if conditions else "TRUE"
    offset = (page - 1) * page_size

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM canonical_events WHERE {where}", params)
                total = cur.fetchone()[0]
                total_pages = math.ceil(total / page_size) if total > 0 else 0

                cur.execute(f"""
                    SELECT canonical_event_id, event_category, severity,
                           description, city, state, country, district,
                           latitude, longitude,
                           classified_category, classification_confidence,
                           credibility_score,
                           verification_status, verification_reasons, cluster_id,
                           source_count, report_count,
                           first_seen, last_seen, created_at
                    FROM canonical_events WHERE {where}
                    ORDER BY {sort_by} {sort_dir}
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                rows = cur.fetchall()

                items = [
                    EventListItem(
                        event_id=str(r[0]),
                        event_category=r[1],
                        severity=r[2],
                        description=r[3][:200] if r[3] else None,
                        city=r[4], state=r[5], country=r[6] or "India",
                        district=r[7],
                        latitude=float(r[8]) if r[8] is not None else None,
                        longitude=float(r[9]) if r[9] is not None else None,
                        classified_category=r[10],
                        classification_confidence=float(r[11]) if r[11] is not None else None,
                        credibility_score=float(r[12]) if r[12] is not None else None,
                        verification_status=r[13] or "pending",
                        verification_reasons=r[14] or [],
                        cluster_id=str(r[15]) if r[15] else None,
                        source_count=r[16] or 1,
                        report_count=r[17] or 1,
                        event_timestamp=_dt_to_iso(r[18]),
                        created_at=_dt_to_iso(r[20]),
                    )
                    for r in rows
                ]
                return EventListResponse(
                    items=items, page=page, page_size=page_size,
                    total=total, total_pages=total_pages,
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)


# ── GET /events/stats (BEFORE /{event_id}) ────────────────────────


@router.get("/events/stats", response_model=StatsResponse)
async def get_stats(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
):
    """Dashboard KPI aggregation — all derived from canonical_events."""
    conditions: list[str] = []
    params: list = []
    if start_time:
        conditions.append("last_seen >= %s"); params.append(start_time)
    if end_time:
        conditions.append("last_seen <= %s"); params.append(end_time)
    if city:
        conditions.append("city = %s"); params.append(city)
    where = " AND ".join(conditions) if conditions else "TRUE"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM canonical_events WHERE {where}", params)
                total_events = cur.fetchone()[0]

                cur.execute(
                    f"SELECT AVG(credibility_score) FROM canonical_events "
                    f"WHERE {where} AND credibility_score IS NOT NULL",
                    params,
                )
                avg_cred = cur.fetchone()[0]

                cur.execute(
                    f"SELECT DATE(last_seen) as d, COUNT(*) "
                    f"FROM canonical_events WHERE {where} GROUP BY d ORDER BY d",
                    params,
                )
                events_over_time = [
                    {"date": str(r[0]), "count": r[1]} for r in cur.fetchall()
                ]

        return StatsResponse(
            total_events=total_events,
            by_category=_fetch_ce_distribution(where, params, "event_category"),
            by_severity=_fetch_ce_distribution(where, params, "severity"),
            by_city=_fetch_ce_distribution(where, params, "city"),
            by_verification_status=_fetch_ce_distribution(where, params, "verification_status"),
            by_source_type={},  # canonical events don't have a single source_type
            average_credibility_score=round(float(avg_cred), 3) if avg_cred else None,
            events_over_time=events_over_time,
        )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)


# ── GET /events/map (BEFORE /{event_id}) ──────────────────────────


@router.get("/events/map", response_model=MapResponse)
async def get_map_events(
    min_lat: float = Query(6.0),
    max_lat: float = Query(38.0),
    min_lon: float = Query(68.0),
    max_lon: float = Query(98.0),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
):
    """Geospatial map data — one marker per canonical event."""
    if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
        _error("INVALID_COORDINATES", "Latitude must be -90 to 90", 400)
    if not (-180 <= min_lon <= 180) or not (-180 <= max_lon <= 180):
        _error("INVALID_COORDINATES", "Longitude must be -180 to 180", 400)
    if min_lat > max_lat or min_lon > max_lon:
        _error("INVALID_COORDINATES", "min must be less than max", 400)

    conditions = ["geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)"]
    params: list = [min_lon, min_lat, max_lon, max_lat]
    if category:
        conditions.append("event_category = %s"); params.append(category)
    if severity:
        conditions.append("severity = %s"); params.append(severity)
    if verification_status:
        conditions.append("verification_status = %s"); params.append(verification_status)
    if start_time:
        conditions.append("last_seen >= %s"); params.append(start_time)
    if end_time:
        conditions.append("last_seen <= %s"); params.append(end_time)
    if city:
        conditions.append("city = %s"); params.append(city)

    where = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT canonical_event_id, latitude, longitude, event_category,
                           severity, city, credibility_score,
                           verification_status, last_seen
                    FROM canonical_events WHERE {where}
                    ORDER BY last_seen DESC LIMIT 1000
                """, params)
                rows = cur.fetchall()

                events = [
                    MapEvent(
                        event_id=str(r[0]),
                        latitude=float(r[1]) if r[1] is not None else None,
                        longitude=float(r[2]) if r[2] is not None else None,
                        event_category=r[3], severity=r[4], city=r[5],
                        credibility_score=float(r[6]) if r[6] is not None else None,
                        verification_status=r[7] or "pending",
                        event_timestamp=_dt_to_iso(r[8]),
                    )
                    for r in rows
                ]
                return MapResponse(
                    events=events, count=len(events),
                    bbox={"min_lat": min_lat, "max_lat": max_lat,
                          "min_lon": min_lon, "max_lon": max_lon},
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)


# ── GET /events/{event_id} (AFTER /stats and /map) ───────────────


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event(event_id: str):
    """Retrieve a single canonical event by UUID with full detail."""
    try:
        uuid.UUID(event_id)
    except ValueError:
        _error("INVALID_UUID", f"Invalid UUID: {event_id}", 400)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Try canonical_events first
                cur.execute("""
                    SELECT canonical_event_id, event_category, severity, description,
                           latitude, longitude, city, district, state, country,
                           first_seen, last_seen,
                           source_count, report_count, contributing_sources,
                           classified_category, classification_confidence,
                           credibility_score, credibility_reasons, cluster_id,
                           verification_status, verification_reasons,
                           verified_by, verification_timestamp,
                           created_at, updated_at
                    FROM canonical_events WHERE canonical_event_id = %s
                """, (event_id,))
                row = cur.fetchone()

                if not row:
                    _error("EVENT_NOT_FOUND", f"Event not found: {event_id}", 404)

                # Get contributing source records for social media / detailed source info
                cur.execute("""
                    SELECT source_id, source_type, source_name, source_url,
                           source_trust_score, hashtags, author_id, platform,
                           photo_urls, video_urls
                    FROM events WHERE canonical_event_id = %s
                    ORDER BY event_timestamp DESC LIMIT 1
                """, (event_id,))
                src_row = cur.fetchone()

                # Verification history from source records
                cur.execute("""
                    SELECT log_id, action, performed_by, notes, performed_at
                    FROM verification_log WHERE event_id IN (
                        SELECT event_id FROM events WHERE canonical_event_id = %s
                    )
                    ORDER BY performed_at DESC
                """, (event_id,))
                history = [
                    {
                        "log_id": str(l[0]), "action": l[1],
                        "performed_by": l[2], "notes": l[3],
                        "performed_at": _dt_to_iso(l[4]),
                    }
                    for l in cur.fetchall()
                ]

                # Build source info from contributing records
                if src_row:
                    src = EventDetailSource(
                        source_id=src_row[0], source_type=src_row[1],
                        source_name=src_row[2], source_url=src_row[3],
                        source_trust_score=float(src_row[4]) if src_row[4] is not None else None,
                    )
                    social = EventDetailSocialMetadata(
                        hashtags=src_row[5] or [], author_id=src_row[6], platform=src_row[7],
                    )
                    media = EventDetailMedia(
                        photo_urls=src_row[8] or [], video_urls=src_row[9] or [],
                    )
                else:
                    src = EventDetailSource()
                    social = EventDetailSocialMetadata()
                    media = EventDetailMedia()

                # Row columns:
                # 0:canonical_event_id 1:event_category 2:severity 3:description
                # 4:latitude 5:longitude 6:city 7:district 8:state 9:country
                # 10:first_seen 11:last_seen 12:source_count 13:report_count
                # 14:contributing_sources 15:classified_category
                # 16:classification_confidence 17:credibility_score
                # 18:credibility_reasons 19:cluster_id 20:verification_status
                # 21:verified_by 22:verification_timestamp 23:created_at 24:updated_at
                # Row columns:
                # 0:canonical_event_id 1:event_category 2:severity 3:description
                # 4:latitude 5:longitude 6:city 7:district 8:state 9:country
                # 10:first_seen 11:last_seen 12:source_count 13:report_count
                # 14:contributing_sources 15:classified_category
                # 16:classification_confidence 17:credibility_score
                # 18:credibility_reasons 19:cluster_id 20:verification_status
                # 21:verification_reasons 22:verified_by
                # 23:verification_timestamp 24:created_at 25:updated_at
                return EventDetailResponse(
                    event_id=str(row[0]),
                    source=src,
                    event_timestamp=_dt_to_iso(row[10]),
                    ingestion_timestamp=_dt_to_iso(row[11]),
                    location=EventDetailLocation(
                        latitude=float(row[4]) if row[4] is not None else None,
                        longitude=float(row[5]) if row[5] is not None else None,
                        city=row[6], district=row[7], state=row[8],
                        country=row[9] or "India",
                    ),
                    event=EventDetailEvent(
                        category=row[1], severity=row[2], description=row[3],
                    ),
                    social_metadata=social,
                    media=media,
                    ai=EventDetailAI(
                        classified_category=row[15],
                        classification_confidence=float(row[16]) if row[16] is not None else None,
                        credibility_score=float(row[17]) if row[17] is not None else None,
                        credibility_reasons=row[18] or [],
                        cluster_id=str(row[19]) if row[19] else None,
                    ),
                    verification=EventDetailVerification(
                        status=row[20] or "pending",
                        verification_reasons=row[21] or [],
                        verified_by=row[22],
                        verification_timestamp=_dt_to_iso(row[23]),
                        history=history,
                    ),
                    source_count=row[12] or 1,
                    report_count=row[13] or 1,
                    created_at=_dt_to_iso(row[24]),
                    updated_at=_dt_to_iso(row[25]),
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)
