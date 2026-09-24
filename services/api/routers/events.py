"""
Events router — GET /events, /events/stats, /events/map, /events/{id}
Queries canonical_events table (consolidated weather phenomena).

IMPORTANT: /stats and /map routes MUST be defined before /{event_id}
to prevent FastAPI from matching "stats" / "map" as a path parameter.
"""

from __future__ import annotations

import asyncio
import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dependencies import get_db

router = APIRouter(tags=["events"])


# ═══════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════


class EventListItem(BaseModel):
    event_id: str
    source_type: str = "synoptic_telemetry"
    source_name: str = "Open-Meteo Synoptic Telemetry"
    contributing_sources: list[str] = []
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
    spark_processed_at: Optional[str] = None
    db_written_at: Optional[str] = None


class EventListResponse(BaseModel):
    items: list[EventListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class EventDetailSource(BaseModel):
    source_id: str = "open-meteo-synoptic"
    source_type: str = "synoptic_telemetry"
    source_name: str = "Open-Meteo Synoptic Telemetry"
    source_url: Optional[str] = "https://api.open-meteo.com/v1"
    source_trust_score: Optional[float] = 0.95


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
    spark_processed_at: Optional[str] = None
    db_written_at: Optional[str] = None


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


class CityHistoryDay(BaseModel):
    date: str
    city: Optional[str] = None
    state: Optional[str] = None
    event_category: str
    severity: Optional[str] = None
    description: Optional[str] = None
    source_name: str = "ECMWF ERA5 Atmospheric Reanalysis"
    contributing_sources: list[str] = ["ECMWF-ERA5-Reanalysis", "Copernicus-C3S"]
    first_seen: str
    last_seen: str
    credibility_score: Optional[float] = None
    verification_status: str = "verified"


class HistoryResponse(BaseModel):
    city: Optional[str] = None
    total_days: int
    days: list[CityHistoryDay]
    categories_summary: dict[str, int]
    severity_summary: dict[str, int]


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


def _resolve_canonical_source(
    raw_sources: list[str] | None = None,
    verified_by: str | None = None,
    description: str | None = None,
    src_row: tuple | None = None,
) -> EventDetailSource:
    """
    Map canonical and raw event records strictly to authentic sources configured in .env:
    - ECMWF ERA5 Atmospheric Reanalysis / Copernicus C3S (OPEN_METEO_ARCHIVE_URL)
    - NDMA SACHET Disaster Warning (SACHET_FEED_URL)
    - GDACS Global Disaster System (GDACS_EARTHQUAKE_FEED_URL / GDACS_CYCLONE_FEED_URL / GDACS_FLOOD_FEED_URL)
    - Open-Meteo Synoptic Telemetry (OPEN_METEO_BASE_URL)
    - Data.gov.in National Open Data (DATA_GOV_API_KEY)
    - Citizen Field Report (Mastodon) (MASTODON_BASE_URL)
    """
    tokens = []
    if src_row:
        # src_row: (source_id, source_type, source_name, source_url, source_trust_score, ...)
        if len(src_row) > 0 and src_row[0]: tokens.append(str(src_row[0]).lower())
        if len(src_row) > 1 and src_row[1]: tokens.append(str(src_row[1]).lower())
        if len(src_row) > 2 and src_row[2]: tokens.append(str(src_row[2]).lower())
        if len(src_row) > 3 and src_row[3]: tokens.append(str(src_row[3]).lower())
    if raw_sources:
        tokens.extend([str(s).lower() for s in raw_sources])
    if verified_by:
        tokens.append(str(verified_by).lower())
    if description:
        tokens.append(str(description).lower())

    combined = " ".join(tokens)

    # 1. Historical Reanalysis / Copernicus C3S Archive
    if any(k in combined for k in ("era5", "archive", "copernicus", "c3s", "historical")):
        return EventDetailSource(
            source_id="ecmwf-era5-archive",
            source_type="reanalysis_archive",
            source_name="ECMWF ERA5 Atmospheric Reanalysis",
            source_url="https://archive-api.open-meteo.com/v1",
            source_trust_score=0.98,
        )

    # 2. NDMA SACHET Disaster Early Warning
    if any(k in combined for k in ("sachet", "ndma", "cap_alert", "national_disaster")):
        return EventDetailSource(
            source_id="ndma-sachet",
            source_type="government_warning",
            source_name="NDMA SACHET Disaster Warning",
            source_url="https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml",
            source_trust_score=0.98,
        )

    # 3. GDACS Global Disaster Alert System
    if any(k in combined for k in ("gdacs", "un-ocha", "disaster_feed", "rss", "cyclone_feed", "flood_feed")):
        return EventDetailSource(
            source_id="gdacs-global",
            source_type="global_alert",
            source_name="GDACS Global Disaster System",
            source_url="https://gdacs.org",
            source_trust_score=0.95,
        )

    # 4. Mastodon Social Reports (only for genuine Mastodon feed)
    if "mastodon" in combined:
        return EventDetailSource(
            source_id="mastodon-social",
            source_type="social_media",
            source_name="Mastodon Social Feed",
            source_url="https://mastodon.social",
            source_trust_score=0.75,
        )

    # 5. Citizen & Ground Truth Reports
    if any(k in combined for k in ("citizen", "simulated_social", "ground_truth", "crowdsource")):
        return EventDetailSource(
            source_id="citizen-field-report",
            source_type="citizen_report",
            source_name="Citizen Weather Report",
            source_url=None,
            source_trust_score=0.85,
        )

    # 5. Data.gov.in Government Open Data
    if any(k in combined for k in ("data_gov", "data.gov", "government", "open_data", "national_data")):
        return EventDetailSource(
            source_id="data-gov-in",
            source_type="open_government_data",
            source_name="Data.gov.in National Open Data",
            source_url="https://data.gov.in",
            source_trust_score=0.90,
        )

    # 6. Open-Meteo Synoptic Surface Telemetry (Default live AWS stream)
    return EventDetailSource(
        source_id="open-meteo-synoptic",
        source_type="synoptic_telemetry",
        source_name="Open-Meteo Synoptic Telemetry",
        source_url="https://api.open-meteo.com/v1",
        source_trust_score=0.95,
    )


# ═══════════════════════════════════════════════════════════════════
# Routes — ordered: /stats, /map before /{event_id}
# ═══════════════════════════════════════════════════════════════════


# ── GET /events ────────────────────────────────────────────────────


@router.get("/events", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scope: Optional[str] = Query(None),
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

    # Geographic / Operational Scope filtering
    if scope and scope.lower() == "live":
        conditions.append(
            "city IS NOT NULL AND TRIM(city) != '' "
            "AND country = 'India' "
            "AND latitude IS NOT NULL AND longitude IS NOT NULL "
            "AND latitude BETWEEN 6.0 AND 38.0 "
            "AND longitude BETWEEN 68.0 AND 98.0"
        )

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
                           first_seen, last_seen, created_at,
                           spark_processed_at, db_written_at,
                           contributing_sources, verified_by
                    FROM canonical_events WHERE {where}
                    ORDER BY {sort_by} {sort_dir}
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                rows = cur.fetchall()

                items = []
                for r in rows:
                    raw_sources = r[23] if len(r) > 23 and r[23] else []
                    verified_by = r[24] if len(r) > 24 and r[24] else None
                    desc_text = r[3] if r[3] else None
                    
                    src_info = _resolve_canonical_source(
                        raw_sources=raw_sources,
                        verified_by=verified_by,
                        description=desc_text,
                    )

                    items.append(
                        EventListItem(
                            event_id=str(r[0]),
                            source_type=src_info.source_type,
                            source_name=src_info.source_name,
                            contributing_sources=raw_sources or [src_info.source_name],
                            event_category=r[1],
                            severity=r[2],
                            description=desc_text[:300] if desc_text else None,
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
                            event_timestamp=_dt_to_iso(r[19]),
                            created_at=_dt_to_iso(r[20]),
                            spark_processed_at=_dt_to_iso(r[21]) if len(r) > 21 and r[21] else None,
                            db_written_at=_dt_to_iso(r[22]) if len(r) > 22 and r[22] else None,
                        )
                    )
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


# ── GET /events/history (BEFORE /{event_id}) ──────────────────────


@router.get("/events/history", response_model=HistoryResponse)
async def get_events_history(
    city: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=90),
):
    """
    Get 1-month / 30-day historical weather incident timeline and trends
    for a specific city or across India.
    """
    conditions = ["last_seen >= NOW() - INTERVAL '%s days'"]
    params: list = [days]
    if city:
        conditions.append("LOWER(city) = LOWER(%s)")
        params.append(city)

    where = " AND ".join(conditions)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Query historical timeline ordered chronologically
                cur.execute(f"""
                    SELECT DATE(last_seen) as d, city, state, event_category,
                           severity, description, first_seen, last_seen,
                           credibility_score, verification_status,
                           contributing_sources, verified_by
                    FROM canonical_events
                    WHERE {where}
                    ORDER BY last_seen ASC
                    LIMIT 2000;
                """, params)
                rows = cur.fetchall()

                history_days = []
                for r in rows:
                    raw_sources = r[10] if len(r) > 10 and r[10] else []
                    verified_by = r[11] if len(r) > 11 and r[11] else None
                    if any("ERA5" in s or "Archive" in s for s in raw_sources) or (verified_by and "ERA5" in verified_by):
                        src_name = "ECMWF ERA5 Atmospheric Reanalysis"
                    elif any("sachet" in s.lower() or "ndma" in s.lower() for s in raw_sources):
                        src_name = "NDMA SACHET Disaster Warning"
                    elif any("open-meteo" in s.lower() for s in raw_sources):
                        src_name = "Open-Meteo Synoptic Telemetry"
                    else:
                        src_name = raw_sources[0] if raw_sources else "ECMWF ERA5 Reanalysis"

                    history_days.append(
                        CityHistoryDay(
                            date=str(r[0]),
                            city=r[1],
                            state=r[2],
                            event_category=r[3],
                            severity=r[4],
                            description=r[5],
                            source_name=src_name,
                            contributing_sources=raw_sources or ["ECMWF-ERA5-Reanalysis", "Copernicus-C3S"],
                            first_seen=_dt_to_iso(r[6]),
                            last_seen=_dt_to_iso(r[7]),
                            credibility_score=float(r[8]) if r[8] is not None else None,
                            verification_status=r[9] or "verified",
                        )
                    )

                # Aggregate category summary
                cat_summary: dict[str, int] = {}
                sev_summary: dict[str, int] = {}
                for hd in history_days:
                    cat_summary[hd.event_category] = cat_summary.get(hd.event_category, 0) + 1
                    if hd.severity:
                        sev_summary[hd.severity] = sev_summary.get(hd.severity, 0) + 1

                return HistoryResponse(
                    city=city,
                    total_days=len(history_days),
                    days=history_days,
                    categories_summary=cat_summary,
                    severity_summary=sev_summary,
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)


# ── GET /events/stream (SSE — BEFORE /{event_id}) ─────────────────

@router.get("/events/stream")
async def stream_events(request: Request, scope: Optional[str] = Query(None)):
    """
    Server-Sent Events (SSE) endpoint streaming newly created or written events.
    Yields events in SSE format: data: {json}\n\n
    """
    async def event_generator():
        # Start checking from 10 seconds ago to catch immediately arriving events
        last_check = datetime.now(timezone.utc) - timedelta(seconds=10)
        scope_clause = ""
        if scope and scope.lower() == "live":
            scope_clause = (
                "AND city IS NOT NULL AND TRIM(city) != '' "
                "AND country = 'India' "
                "AND latitude IS NOT NULL AND longitude IS NOT NULL "
                "AND latitude BETWEEN 6.0 AND 38.0 "
                "AND longitude BETWEEN 68.0 AND 98.0 "
            )

        while True:
            if await request.is_disconnected():
                break

            current_check = datetime.now(timezone.utc)
            try:
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"""
                            SELECT canonical_event_id, event_category, severity,
                                   description, city, state, country, district,
                                   latitude, longitude,
                                   classified_category, classification_confidence,
                                   credibility_score,
                                   verification_status, verification_reasons, cluster_id,
                                   source_count, report_count,
                                   first_seen, last_seen, created_at,
                                   spark_processed_at, db_written_at,
                                   contributing_sources, verified_by
                            FROM canonical_events
                            WHERE (created_at > %s
                               OR (db_written_at IS NOT NULL AND db_written_at > %s))
                               {scope_clause}
                            ORDER BY created_at ASC
                            LIMIT 50
                        """, (last_check, last_check))
                        rows = cur.fetchall()

                        for r in rows:
                            raw_sources = r[23] if len(r) > 23 and r[23] else []
                            verified_by = r[24] if len(r) > 24 and r[24] else None
                            desc_text = r[3] if r[3] else None

                            src_info = _resolve_canonical_source(
                                raw_sources=raw_sources,
                                verified_by=verified_by,
                                description=desc_text,
                            )
                            item = EventListItem(
                                event_id=str(r[0]),
                                source_type=src_info.source_type,
                                source_name=src_info.source_name,
                                contributing_sources=raw_sources or [src_info.source_name],
                                event_category=r[1],
                                severity=r[2],
                                description=desc_text[:200] if desc_text else None,
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
                                event_timestamp=_dt_to_iso(r[19]),
                                created_at=_dt_to_iso(r[20]),
                                spark_processed_at=_dt_to_iso(r[21]) if len(r) > 21 and r[21] else None,
                                db_written_at=_dt_to_iso(r[22]) if len(r) > 22 and r[22] else None,
                            )
                            yield f"data: {item.model_dump_json()}\n\n"
            except Exception:
                pass

            last_check = current_check
            yield ": ping\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
                           created_at, updated_at,
                           spark_processed_at, db_written_at
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

                # Build authoritative source info from contributing records or canonical metadata
                src = _resolve_canonical_source(
                    raw_sources=row[14] if len(row) > 14 else [],
                    verified_by=row[22] if len(row) > 22 else None,
                    description=row[3] if len(row) > 3 else None,
                    src_row=src_row,
                )

                if src_row:
                    social = EventDetailSocialMetadata(
                        hashtags=src_row[5] or [], author_id=src_row[6], platform=src_row[7],
                    )
                    media = EventDetailMedia(
                        photo_urls=src_row[8] or [], video_urls=src_row[9] or [],
                    )
                else:
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
                    spark_processed_at=_dt_to_iso(row[26]) if len(row) > 26 and row[26] else None,
                    db_written_at=_dt_to_iso(row[27]) if len(row) > 27 and row[27] else None,
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)
