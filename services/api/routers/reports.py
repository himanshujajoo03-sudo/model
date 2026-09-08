"""
Reports router — GET /reports, GET /reports/{report_id}
Queries the events table (individual source records / ingestion records).

IMPORTANT: /stats route MUST be defined before /{report_id}
to prevent FastAPI from matching "stats" as a path parameter.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from dependencies import get_db

router = APIRouter(tags=["reports"])


# ═══════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════


class ReportListItem(BaseModel):
    report_id: str
    source_id: str
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    source_trust_score: Optional[float] = None
    event_timestamp: str
    ingestion_timestamp: str
    event_category: str
    severity: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    classified_category: Optional[str] = None
    classification_confidence: Optional[float] = None
    credibility_score: Optional[float] = None
    credibility_reasons: list[str] = []
    duplicate_score: Optional[float] = None
    verification_status: str = "pending"
    canonical_event_id: Optional[str] = None
    created_at: str


class ReportListResponse(BaseModel):
    items: list[ReportListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class ReportDetailResponse(BaseModel):
    report_id: str
    source_id: str
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    source_trust_score: Optional[float] = None
    event_timestamp: str
    ingestion_timestamp: str
    event_category: str
    severity: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    classified_category: Optional[str] = None
    classification_confidence: Optional[float] = None
    credibility_score: Optional[float] = None
    credibility_reasons: list[str] = []
    duplicate_score: Optional[float] = None
    verification_status: str = "pending"
    verified_by: Optional[str] = None
    verification_timestamp: Optional[str] = None
    canonical_event_id: Optional[str] = None
    canonical_event_category: Optional[str] = None
    canonical_event_severity: Optional[str] = None
    canonical_event_city: Optional[str] = None
    created_at: str
    updated_at: str


class ReportStatsResponse(BaseModel):
    total_reports: int
    by_source_type: dict[str, int]
    by_verification_status: dict[str, int]
    by_category: dict[str, int]
    linked_to_canonical: int
    unlinked: int


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


def _fetch_distribution(table: str, where: str, params: list, col: str) -> dict[str, int]:
    """Fetch count distribution for a given column."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {col}, COUNT(*) FROM {table} "
                f"WHERE {where} AND {col} IS NOT NULL "
                f"GROUP BY {col} ORDER BY COUNT(*) DESC",
                params,
            )
            return {row[0]: row[1] for row in cur.fetchall()}


# ═══════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════


# ── GET /reports/stats (BEFORE /{report_id}) ─────────────────────


@router.get("/reports/stats", response_model=ReportStatsResponse)
async def get_report_stats():
    """Source record statistics — derived from the events table."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM events")
                total = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM events WHERE canonical_event_id IS NOT NULL"
                )
                linked = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM events WHERE canonical_event_id IS NULL"
                )
                unlinked = cur.fetchone()[0]

        return ReportStatsResponse(
            total_reports=total,
            by_source_type=_fetch_distribution("events", "TRUE", [], "source_type"),
            by_verification_status=_fetch_distribution("events", "TRUE", [], "verification_status"),
            by_category=_fetch_distribution("events", "TRUE", [], "event_category"),
            linked_to_canonical=linked,
            unlinked=unlinked,
        )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)


# ── GET /reports ──────────────────────────────────────────────────


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = Query(None),
    source_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    has_canonical: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("event_timestamp"),
    sort_order: str = Query("desc"),
):
    """List individual source records (reports) with pagination and filtering."""
    allowed_sort = {
        "event_timestamp", "ingestion_timestamp", "credibility_score",
        "duplicate_score", "event_category", "severity", "city",
        "source_type", "verification_status", "created_at",
    }
    if sort_by not in allowed_sort:
        sort_by = "event_timestamp"
    sort_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

    conditions: list[str] = []
    params: list = []

    if source_type:
        conditions.append("source_type = %s"); params.append(source_type)
    if source_name:
        conditions.append("source_name = %s"); params.append(source_name)
    if category:
        conditions.append("event_category = %s"); params.append(category)
    if severity:
        conditions.append("severity = %s"); params.append(severity)
    if verification_status:
        conditions.append("verification_status = %s"); params.append(verification_status)
    if city:
        conditions.append("city = %s"); params.append(city)
    if has_canonical is True:
        conditions.append("canonical_event_id IS NOT NULL")
    elif has_canonical is False:
        conditions.append("canonical_event_id IS NULL")
    if search:
        conditions.append(
            "(source_id ILIKE %s OR source_name ILIKE %s OR city ILIKE %s OR description ILIKE %s)"
        )
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])

    where = " AND ".join(conditions) if conditions else "TRUE"
    offset = (page - 1) * page_size

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM events WHERE {where}", params)
                total = cur.fetchone()[0]
                total_pages = math.ceil(total / page_size) if total > 0 else 0

                cur.execute(f"""
                    SELECT event_id, source_id, source_type, source_name,
                           source_url, source_trust_score,
                           event_timestamp, ingestion_timestamp,
                           event_category, severity, description,
                           city, state, district, country,
                           latitude, longitude,
                           classified_category, classification_confidence,
                           credibility_score, credibility_reasons,
                           duplicate_score, verification_status,
                           canonical_event_id, created_at
                    FROM events WHERE {where}
                    ORDER BY {sort_by} {sort_dir}
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                rows = cur.fetchall()

                items = [
                    ReportListItem(
                        report_id=str(r[0]),
                        source_id=r[1],
                        source_type=r[2],
                        source_name=r[3],
                        source_url=r[4],
                        source_trust_score=float(r[5]) if r[5] is not None else None,
                        event_timestamp=_dt_to_iso(r[6]),
                        ingestion_timestamp=_dt_to_iso(r[7]),
                        event_category=r[8],
                        severity=r[9],
                        description=r[10][:200] if r[10] else None,
                        city=r[11],
                        state=r[12],
                        district=r[13],
                        country=r[14] or "India",
                        latitude=float(r[15]) if r[15] is not None else None,
                        longitude=float(r[16]) if r[16] is not None else None,
                        classified_category=r[17],
                        classification_confidence=float(r[18]) if r[18] is not None else None,
                        credibility_score=float(r[19]) if r[19] is not None else None,
                        credibility_reasons=r[20] or [],
                        duplicate_score=float(r[21]) if r[21] is not None else None,
                        verification_status=r[22] or "pending",
                        canonical_event_id=str(r[23]) if r[23] else None,
                        created_at=_dt_to_iso(r[24]),
                    )
                    for r in rows
                ]
                return ReportListResponse(
                    items=items, page=page, page_size=page_size,
                    total=total, total_pages=total_pages,
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)


# ── GET /reports/{report_id} ─────────────────────────────────────


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report(report_id: str):
    """Retrieve a single source record (report) by UUID with full detail."""
    try:
        uuid.UUID(report_id)
    except ValueError:
        _error("INVALID_UUID", f"Invalid UUID: {report_id}", 400)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT event_id, source_id, source_type, source_name,
                           source_url, source_trust_score,
                           event_timestamp, ingestion_timestamp,
                           event_category, severity, description,
                           city, state, district, country,
                           latitude, longitude,
                           classified_category, classification_confidence,
                           credibility_score, credibility_reasons,
                           duplicate_score, verification_status,
                           verified_by, verification_timestamp,
                           canonical_event_id, created_at, updated_at
                    FROM events WHERE event_id = %s
                """, (report_id,))
                row = cur.fetchone()

                if not row:
                    _error("REPORT_NOT_FOUND", f"Report not found: {report_id}", 404)

                # Fetch linked canonical event info if available
                ce_category = None
                ce_severity = None
                ce_city = None
                if row[25]:  # canonical_event_id at index 25
                    cur.execute("""
                        SELECT event_category, severity, city
                        FROM canonical_events WHERE canonical_event_id = %s
                    """, (str(row[25]),))
                    ce_row = cur.fetchone()
                    if ce_row:
                        ce_category = ce_row[0]
                        ce_severity = ce_row[1]
                        ce_city = ce_row[2]

                return ReportDetailResponse(
                    report_id=str(row[0]),
                    source_id=row[1],
                    source_type=row[2],
                    source_name=row[3],
                    source_url=row[4],
                    source_trust_score=float(row[5]) if row[5] is not None else None,
                    event_timestamp=_dt_to_iso(row[6]),
                    ingestion_timestamp=_dt_to_iso(row[7]),
                    event_category=row[8],
                    severity=row[9],
                    description=row[10],
                    city=row[11],
                    state=row[12],
                    district=row[13],
                    country=row[14] or "India",
                    latitude=float(row[15]) if row[15] is not None else None,
                    longitude=float(row[16]) if row[16] is not None else None,
                    classified_category=row[17],
                    classification_confidence=float(row[18]) if row[18] is not None else None,
                    credibility_score=float(row[19]) if row[19] is not None else None,
                    credibility_reasons=row[20] or [],
                    duplicate_score=float(row[21]) if row[21] is not None else None,
                    verification_status=row[22] or "pending",
                    verified_by=row[23],
                    verification_timestamp=_dt_to_iso(row[24]),
                    canonical_event_id=str(row[25]) if row[25] else None,
                    canonical_event_category=ce_category,
                    canonical_event_severity=ce_severity,
                    canonical_event_city=ce_city,
                    created_at=_dt_to_iso(row[26]),
                    updated_at=_dt_to_iso(row[27]),
                )
    except HTTPException:
        raise
    except Exception as e:
        _error("DATABASE_UNAVAILABLE", f"Query failed: {type(e).__name__}", 503)
