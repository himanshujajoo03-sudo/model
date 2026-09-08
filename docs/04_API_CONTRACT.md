# 04 — API Contract

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `04_API_CONTRACT.md`
**Version:** 1.0
**Status:** AWAITING APPROVAL
**Derived from:** `01_ARCHITECTURE.md` v1.3 + `02_DATA_SCHEMA.md` v1.1 + `03_KAFKA_CONTRACT.md` v1.0
**Last updated:** 2026-09-01

---

## Change Control

No endpoint name, HTTP method, request/response schema, authentication mechanism,
or API-to-Kafka/database integration pattern may be changed without updating this
document first and obtaining architect sign-off.

---

## 1. Document Metadata

This document is the **single source of truth for the FastAPI REST API contract**.
It defines every endpoint, request/response model, authentication mechanism,
error structure, and integration boundary between the API service and the
rest of the platform.

**Scope:** MVP hackathon (5-day sprint).
**Port:** 8000
**Base URL:** `http://localhost:8000/api/v1`

---

## 2. API Overview

| Property | Value |
|----------|-------|
| Framework | FastAPI (Python 3.11+) |
| Base URL | `/api/v1` |
| Port | `8000` (mapped from Docker container) |
| Request format | JSON (`application/json`) |
| Response format | JSON (`application/json`) |
| Timestamp format | ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SS.sssZ`) per `02_DATA_SCHEMA.md §4` |
| UUID format | UUID v4 (RFC 4122) per `02_DATA_SCHEMA.md §5` |
| API versioning | URL path prefix `/api/v1`. Future versions: `/api/v2` |
| Auto-generated docs | Swagger UI at `/docs`, ReDoc at `/redoc`, OpenAPI schema at `/openapi.json` |

### 2.1 Service Boundaries

The API service is responsible for:

- Serving read queries against PostgreSQL/PostGIS
- Accepting citizen report submissions and producing to `citizen.raw`
- Accepting admin verification actions, updating PostgreSQL, and producing to `weather.verified`
- Health checks

The API service is **NOT** responsible for:

- Spark processing or ML enrichment (those run inside Spark)
- Consuming Kafka raw topics (Spark does that)
- Writing events to PostgreSQL (the PostgreSQL writer consumer does that)

---

## 3. Authentication

**Resolves architecture open question #3:** JWT Bearer token authentication
for admin endpoints.

### 3.1 Mechanism

| Aspect | Decision |
|--------|----------|
| Method | JWT Bearer tokens |
| Token lifetime | 8 hours (configurable via `JWT_EXPIRATION_HOURS`) |
| Secret key | Loaded from environment variable `JWT_SECRET_KEY` — **never hardcoded** |
| Algorithm | HS256 |
| Storage | Token passed in `Authorization: Bearer <token>` header |

### 3.2 Public vs Protected Endpoints

| Endpoint | Authentication | Rationale |
|----------|---------------|-----------|
| `GET /api/v1/health` | **None** | Used by Docker healthcheck and monitoring |
| `GET /api/v1/events` | **None** | Public dashboard data |
| `GET /api/v1/events/{event_id}` | **None** | Public event detail |
| `GET /api/v1/events/stats` | **None** | Public dashboard KPIs |
| `GET /api/v1/events/map` | **None** | Public map data |
| `POST /api/v1/citizen-reports` | **None** | Citizen submission — no auth required |
| `POST /api/v1/auth/login` | **None** | Login endpoint itself is public |
| `POST /api/v1/verification` | **Required** | Admin-only action |

### 3.3 Environment Variables

```
JWT_SECRET_KEY=<random-secret>          # Required; app refuses to start without it
JWT_EXPIRATION_HOURS=8                  # Optional; defaults to 8
ADMIN_USERNAME=admin                    # Default admin username
ADMIN_PASSWORD=<hashed-password>        # Bcrypt hash; never plaintext
```

> `.env` is gitignored. `.env.example` is committed with placeholder values only.
> The API must refuse to start if `JWT_SECRET_KEY` is not set.

---

## 4. Common API Conventions

### 4.1 Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes (for POST/PUT) |
| `Authorization` | `Bearer <jwt-token>` | Only on protected endpoints |

### 4.2 Timestamp Format

All timestamps in requests and responses use ISO 8601 with UTC offset:
```
YYYY-MM-DDTHH:MM:SS.sssZ
```

Examples:
```
2026-08-31T14:30:00.000Z        ✅ valid
2026-08-31T20:00:00.000+05:30   ✅ valid
2026-08-31 14:30:00             ❌ invalid
```

### 4.3 UUID Format

All identifiers use UUID v4 (lowercase, hyphenated):
```
a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### 4.4 Pagination

Supported on list endpoints via query parameters:

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `page` | integer | `1` | ≥ 1 | Page number (1-indexed) |
| `page_size` | integer | `20` | 1–100 | Items per page |

Response includes pagination metadata:
```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

### 4.5 Filtering

List endpoints support query-parameter filters. All filters are optional and
combinable. Unknown filter parameters are ignored (not rejected).

| Filter | Type | Applies To | Description |
|--------|------|-----------|-------------|
| `city` | string | `/events`, `/events/map` | Exact match on city name |
| `district` | string | `/events` | Exact match on district name |
| `state` | string | `/events`, `/events/map` | Exact match on state name |
| `category` | string (enum) | `/events`, `/events/map`, `/events/stats` | Event category per `02_DATA_SCHEMA.md §1.2` |
| `severity` | string (enum) | `/events`, `/events/map`, `/events/stats` | Severity per `02_DATA_SCHEMA.md §1.3` |
| `verification_status` | string (enum) | `/events`, `/events/stats` | Per `02_DATA_SCHEMA.md §1.4` |
| `source_type` | string (enum) | `/events`, `/events/stats` | Per `02_DATA_SCHEMA.md §1.1` |
| `start_time` | ISO 8601 UTC | `/events`, `/events/map`, `/events/stats` | Lower bound (inclusive) on `event_timestamp` |
| `end_time` | ISO 8601 UTC | `/events`, `/events/map`, `/events/stats` | Upper bound (inclusive) on `event_timestamp` |
| `min_credibility` | float 0–1 | `/events` | Minimum `credibility_score` |
| `min_lat` | float | `/events/map` | Bounding box south |
| `max_lat` | float | `/events/map` | Bounding box north |
| `min_lon` | float | `/events/map` | Bounding box west |
| `max_lon` | float | `/events/map` | Bounding box east |

### 4.6 Sorting

| Endpoint | Default Sort | Supports Sort Parameter? |
|----------|-------------|------------------------|
| `GET /events` | `event_timestamp DESC` | Yes — `sort_by` (e.g., `event_timestamp`, `created_at`, `credibility_score`) and `sort_order` (`asc` / `desc`) |
| `GET /events/{id}` | N/A (single item) | No |
| `GET /events/stats` | N/A (aggregation) | No |
| `GET /events/map` | `event_timestamp DESC` | No |

---

## 5. Standard Error Response

All error responses follow a consistent structure:

```json
{
  "error": {
    "code": "EVENT_NOT_FOUND",
    "message": "Event not found",
    "details": null,
    "timestamp": "2026-08-31T14:30:00.000Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Machine-readable error code (UPPER_SNAKE_CASE) |
| `message` | string | Human-readable error description |
| `details` | object \| null | Additional context (e.g., field validation errors) |
| `timestamp` | ISO 8601 UTC | Time the error occurred |

### 5.1 HTTP Status Codes

| Status | Meaning | When Used |
|--------|---------|-----------|
| `200 OK` | Success | Successful GET, successful verification |
| `201 Created` | Resource created | Successful citizen report submission |
| `400 Bad Request` | Client error | Malformed JSON, missing required fields, invalid enum value |
| `401 Unauthorized` | Authentication required | Missing or invalid JWT token on protected endpoints |
| `403 Forbidden` | Authenticated but not permitted | Valid token but insufficient permissions (future use) |
| `404 Not Found` | Resource not found | `event_id` does not exist in database |
| `409 Conflict` | Conflict | Duplicate citizen report (same source_id already processed) |
| `422 Unprocessable Entity` | Validation error | Pydantic validation failure (type mismatch, out-of-range values) |
| `500 Internal Server Error` | Server error | Unexpected failure (logged; stack trace in server logs only) |
| `503 Service Unavailable` | Dependency unavailable | PostgreSQL or Kafka unreachable during health check |

### 5.2 Error Code Catalogue

| Code | HTTP Status | Description |
|------|------------|-------------|
| `INVALID_JSON` | 400 | Request body is not valid JSON |
| `MISSING_REQUIRED_FIELD` | 400 | Required field is missing or null |
| `INVALID_ENUM_VALUE` | 400 | Field value not in allowed enum |
| `INVALID_UUID` | 400 | Path parameter is not a valid UUID v4 |
| `INVALID_COORDINATES` | 400 | Latitude/longitude out of range or mismatched |
| `MEDIA_TOO_LARGE` | 400 | Uploaded file exceeds size limit |
| `MEDIA_INVALID_TYPE` | 400 | Uploaded file type not allowed |
| `UNAUTHORIZED` | 401 | Missing or invalid JWT token |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `EVENT_NOT_FOUND` | 404 | Event with given ID does not exist |
| `DUPLICATE_REPORT` | 409 | Citizen report with same source_id already exists |
| `VALIDATION_ERROR` | 422 | Pydantic model validation failed |
| `DATABASE_UNAVAILABLE` | 503 | PostgreSQL connection failed |
| `KAFKA_UNAVAILABLE` | 503 | Kafka broker unreachable |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## 6. Health Endpoint

### `GET /api/v1/health`

**Purpose:** System health check for Docker healthcheck, monitoring, and frontend status display.

**Authentication:** None

**Query Parameters:** None

#### Response — 200 OK

```json
{
  "status": "healthy",
  "database": "connected",
  "kafka": "connected",
  "timestamp": "2026-08-31T14:30:00.000Z"
}
```

#### Response — 503 Service Unavailable

```json
{
  "status": "degraded",
  "database": "connected",
  "kafka": "unavailable",
  "timestamp": "2026-08-31T14:30:00.000Z"
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `status` | `"healthy"` / `"degraded"` / `"unhealthy"` | Overall status |
| `database` | `"connected"` / `"unavailable"` | PostgreSQL connectivity |
| `kafka` | `"connected"` / `"unavailable"` | Kafka connectivity |
| `timestamp` | ISO 8601 UTC | Time of health check |

**Behavior:**
- If both database and Kafka are connected → `200`, `"healthy"`
- If one dependency is unavailable → `200`, `"degraded"` (API still functions for degraded reads)
- If database is unavailable → `503`, `"unhealthy"` (read endpoints non-functional)
- Health check pings are lightweight: `SELECT 1` for PostgreSQL, `KafkaProducer.list_topics()` for Kafka

---

## 7. Event APIs — Overview

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/events` | GET | No | List and filter events (paginated) |
| `/api/v1/events/{event_id}` | GET | No | Single event detail |
| `/api/v1/events/stats` | GET | No | Dashboard KPI aggregation |
| `/api/v1/events/map` | GET | No | Geospatial map data |

All event endpoints read from PostgreSQL. They do **not** read from Kafka.
The data available is what the PostgreSQL writer has already persisted from
`weather.events`.

---

## 8. `GET /api/v1/events`

**Purpose:** Main dashboard endpoint — filterable, paginated event list.

**Authentication:** None

### Query Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `page` | integer | `1` | No | Page number |
| `page_size` | integer | `20` | No | Items per page (max 100) |
| `city` | string | — | No | Filter by city name |
| `district` | string | — | No | Filter by district name |
| `state` | string | — | No | Filter by state name |
| `category` | string | — | No | Filter by event category |
| `severity` | string | — | No | Filter by severity level |
| `verification_status` | string | — | No | Filter by verification status |
| `source_type` | string | — | No | Filter by source type |
| `start_time` | ISO 8601 UTC | — | No | Events at or after this time |
| `end_time` | ISO 8601 UTC | — | No | Events at or before this time |
| `min_credibility` | float | — | No | Minimum credibility score (0.0–1.0) |
| `sort_by` | string | `event_timestamp` | No | Sort field |
| `sort_order` | string | `desc` | No | `asc` or `desc` |

### Response — 200 OK

```json
{
  "items": [
    {
      "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source_type": "weather_api",
      "source_name": "Open-Meteo",
      "event_timestamp": "2026-08-31T08:15:00.000Z",
      "event_category": "heavy_rainfall",
      "severity": "high",
      "description": "Heavy rainfall has caused waterlogging in several areas...",
      "city": "Mumbai",
      "state": "Maharashtra",
      "country": "India",
      "latitude": 19.076000,
      "longitude": 72.877700,
      "classified_category": "flood",
      "classification_confidence": 0.91,
      "credibility_score": 0.84,
      "duplicate_score": 0.07,
      "verification_status": "pending",
      "cluster_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
      "created_at": "2026-08-31T08:16:03.441Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 142,
  "total_pages": 8
}
```

### Response Fields

Each item in `items` contains the fields required by the dashboard table:

| Field | Type | Source DB Column | Notes |
|-------|------|-----------------|-------|
| `event_id` | UUID v4 | `events.event_id` | Primary key |
| `source_type` | string | `events.source_type` | Per `02_DATA_SCHEMA.md §1.1` |
| `source_name` | string | `events.source_name` | Human-readable source |
| `event_timestamp` | ISO 8601 UTC | `events.event_timestamp` | Event occurrence time |
| `event_category` | string | `events.event_category` | Per `02_DATA_SCHEMA.md §1.2` |
| `severity` | string \| null | `events.severity` | Per `02_DATA_SCHEMA.md §1.3` |
| `description` | string \| null | `events.description` | Truncated to 200 chars in list view |
| `city` | string \| null | `events.city` | City name |
| `state` | string \| null | `events.state` | State name |
| `country` | string | `events.country` | Default "India" |
| `latitude` | float \| null | `events.latitude` | Decimal degrees |
| `longitude` | float \| null | `events.longitude` | Decimal degrees |
| `classified_category` | string \| null | `events.classified_category` | ML-assigned category |
| `classification_confidence` | float \| null | `events.classification_confidence` | ML confidence |
| `credibility_score` | float \| null | `events.credibility_score` | Source credibility |
| `duplicate_score` | float \| null | `events.duplicate_score` | Duplicate likelihood |
| `verification_status` | string | `events.verification_status` | Per `02_DATA_SCHEMA.md §1.4` |
| `cluster_id` | UUID \| null | `events.cluster_id` | Cluster membership |
| `created_at` | ISO 8601 UTC | `events.created_at` | When persisted to DB |

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `INVALID_ENUM_VALUE` | Filter parameter not in allowed enum |
| 422 | `VALIDATION_ERROR` | Query parameter type mismatch |

### SQL Equivalent

```sql
SELECT event_id, source_type, source_name, event_timestamp, event_category,
       severity, LEFT(description, 200) AS description, city, state, country,
       latitude, longitude, classified_category, classification_confidence,
       credibility_score, duplicate_score, verification_status, cluster_id, created_at
FROM events
WHERE ($1::text IS NULL OR city = $1)
  AND ($2::text IS NULL OR state = $2)
  AND ($3::text IS NULL OR event_category = $3)
  AND ($4::text IS NULL OR severity = $4)
  AND ($5::text IS NULL OR verification_status = $5)
  AND ($6::text IS NULL OR source_type = $6)
  AND ($7::timestamptz IS NULL OR event_timestamp >= $7)
  AND ($8::timestamptz IS NULL OR event_timestamp <= $8)
  AND ($9::numeric IS NULL OR credibility_score >= $9)
ORDER BY event_timestamp DESC
LIMIT $10 OFFSET $11;
```

---

## 9. `GET /api/v1/events/{event_id}`

**Purpose:** Full event detail for the Event Details page.

**Authentication:** None

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_id` | UUID v4 | Yes | Event identifier |

### Response — 200 OK

```json
{
  "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "source": {
    "source_id": "openmeteo_mumbai_20260831T1430Z",
    "source_type": "weather_api",
    "source_name": "Open-Meteo",
    "source_url": "https://api.open-meteo.com/v1/forecast",
    "source_trust_score": 0.95
  },
  "event_timestamp": "2026-08-31T08:15:00.000Z",
  "ingestion_timestamp": "2026-08-31T08:16:03.441Z",
  "location": {
    "latitude": 19.076000,
    "longitude": 72.877700,
    "city": "Mumbai",
    "district": "Mumbai City",
    "state": "Maharashtra",
    "country": "India"
  },
  "event": {
    "category": "heavy_rainfall",
    "severity": "high",
    "description": "Heavy rainfall has caused waterlogging in several low-lying areas of Mumbai including Sion, Kurla and Andheri."
  },
  "social_metadata": {
    "hashtags": [],
    "author_id": null,
    "platform": null
  },
  "media": {
    "photo_urls": [],
    "video_urls": []
  },
  "ai": {
    "classified_category": "flood",
    "classification_confidence": 0.91,
    "duplicate_score": 0.07,
    "credibility_score": 0.84,
    "credibility_reasons": [
      "Source has high historical accuracy",
      "5 independent reports within 3 km and 20 minutes",
      "Open-Meteo API confirms heavy precipitation at coordinates",
      "No contradicting reports detected"
    ],
    "cluster_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210"
  },
  "verification": {
    "status": "pending",
    "verified_by": null,
    "verification_timestamp": null,
    "history": [
      {
        "log_id": "b1234567-e890-1234-5678-901234567890",
        "action": "marked_suspicious",
        "performed_by": "admin_01",
        "notes": "Low credibility score; cross-referencing",
        "performed_at": "2026-08-31T10:00:00.000Z"
      }
    ]
  },
  "created_at": "2026-08-31T08:16:03.441Z",
  "updated_at": "2026-08-31T10:00:01.000Z"
}
```

### Response Fields

| Field | Type | Source |
|-------|------|--------|
| `event_id` | UUID v4 | `events.event_id` |
| `source.source_id` | string | `events.source_id` |
| `source.source_type` | string | `events.source_type` |
| `source.source_name` | string | `events.source_name` |
| `source.source_url` | string \| null | `events.source_url` |
| `source.source_trust_score` | float \| null | `events.source_trust_score` |
| `event_timestamp` | ISO 8601 UTC | `events.event_timestamp` |
| `ingestion_timestamp` | ISO 8601 UTC | `events.ingestion_timestamp` |
| `location.*` | object | `events.latitude`, `longitude`, `city`, `district`, `state`, `country` |
| `event.category` | string | `events.event_category` |
| `event.severity` | string \| null | `events.severity` |
| `event.description` | string \| null | `events.description` (full, up to 2000 chars) |
| `social_metadata.*` | object | `events.hashtags`, `author_id`, `platform` |
| `media.photo_urls` | string[] | `events.photo_urls` |
| `media.video_urls` | string[] | `events.video_urls` |
| `ai.*` | object | `events.classified_category`, `classification_confidence`, `duplicate_score`, `credibility_score`, `credibility_reasons`, `cluster_id` |
| `verification.status` | string | `events.verification_status` |
| `verification.verified_by` | string \| null | `events.verified_by` |
| `verification.verification_timestamp` | ISO 8601 UTC \| null | `events.verification_timestamp` |
| `verification.history` | array | Joined from `verification_log` table, ordered by `performed_at DESC` |
| `created_at` | ISO 8601 UTC | `events.created_at` |
| `updated_at` | ISO 8601 UTC | `events.updated_at` |

> Note: The detail response restructures flat DB columns into nested objects
> matching the Canonical Weather Event shape (per `02_DATA_SCHEMA.md §6 preamble`
> JSON→DB mapping, reversed).

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `INVALID_UUID` | `event_id` is not a valid UUID v4 |
| 404 | `EVENT_NOT_FOUND` | No event with this ID exists |

---

## 10. `GET /api/v1/events/stats`

**Purpose:** Dashboard KPI aggregation.

**Authentication:** None

**Type:** Database aggregation (not real-time streaming metrics).

> This endpoint queries PostgreSQL directly. It reflects **persisted** data —
> events that have completed the full pipeline (ingestion → Spark → ML → PostgreSQL).
> It does **not** provide sub-second real-time analytics.

### Query Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `start_time` | ISO 8601 UTC | — | No | Lower bound on event_timestamp |
| `end_time` | ISO 8601 UTC | — | No | Upper bound on event_timestamp |
| `city` | string | — | No | Filter by city |

### Response — 200 OK

```json
{
  "total_events": 1423,
  "by_category": {
    "heavy_rainfall": 312,
    "flood": 198,
    "thunderstorm": 267,
    "heatwave": 145,
    "fog": 89,
    "lightning": 134,
    "other": 278
  },
  "by_severity": {
    "low": 234,
    "moderate": 567,
    "high": 489,
    "extreme": 133
  },
  "by_city": {
    "Mumbai": 612,
    "Nagpur": 489,
    "Nashik": 322
  },
  "by_verification_status": {
    "pending": 890,
    "verified": 312,
    "needs_review": 89,
    "suspicious": 78,
    "duplicate": 54
  },
  "by_source_type": {
    "weather_api": 445,
    "rss": 189,
    "website": 134,
    "citizen": 267,
    "simulated_social": 198,
    "government_dataset": 112,
    "synthetic": 78
  },
  "average_credibility_score": 0.72,
  "events_over_time": [
    {
      "date": "2026-08-31",
      "count": 142
    },
    {
      "date": "2026-09-01",
      "count": 167
    }
  ]
}
```

### Response Structure

| Field | Type | Description |
|-------|------|-------------|
| `total_events` | integer | Total events matching filters |
| `by_category` | object | Count per event category (only non-zero categories included) |
| `by_severity` | object | Count per severity level |
| `by_city` | object | Count per city |
| `by_verification_status` | object | Count per verification status |
| `by_source_type` | object | Count per source type |
| `average_credibility_score` | float | Mean credibility_score across matching events |
| `events_over_time` | array | Daily event counts (for time-series chart) |

### SQL Equivalent (total_events)

```sql
SELECT COUNT(*) FROM events
WHERE ($1::timestamptz IS NULL OR event_timestamp >= $1)
  AND ($2::timestamptz IS NULL OR event_timestamp <= $2)
  AND ($3::text IS NULL OR city = $3);
```

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 503 | `DATABASE_UNAVAILABLE` | PostgreSQL unreachable |

---

## 11. `GET /api/v1/events/map`

**Purpose:** Geospatial data for the Leaflet/MapLibre map view.

**Authentication:** None

**Optimization:** Returns only the fields needed to render map markers — not
full event payloads. This keeps response sizes small for map performance.

### Query Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `min_lat` | float | — | Yes | Bounding box south (−90 to 90) |
| `max_lat` | float | — | Yes | Bounding box north (−90 to 90) |
| `min_lon` | float | — | Yes | Bounding box west (−180 to 180) |
| `max_lon` | float | — | Yes | Bounding box east (−180 to 180) |
| `category` | string | — | No | Filter by event category |
| `severity` | string | — | No | Filter by severity |
| `verification_status` | string | — | No | Filter by verification status |
| `start_time` | ISO 8601 UTC | — | No | Lower bound on event_timestamp |
| `end_time` | ISO 8601 UTC | — | No | Upper bound on event_timestamp |
| `city` | string | — | No | Filter by city |

### Response — 200 OK

```json
{
  "events": [
    {
      "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "latitude": 19.076000,
      "longitude": 72.877700,
      "event_category": "heavy_rainfall",
      "severity": "high",
      "city": "Mumbai",
      "credibility_score": 0.84,
      "verification_status": "pending",
      "event_timestamp": "2026-08-31T08:15:00.000Z"
    }
  ],
  "count": 1,
  "bbox": {
    "min_lat": 18.0,
    "max_lat": 20.0,
    "min_lon": 72.0,
    "max_lon": 73.0
  }
}
```

### Response Fields (Map-Optimized)

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID v4 | For click-through to detail view |
| `latitude` | float | Marker position |
| `longitude` | float | Marker position |
| `event_category` | string | For marker color/icon |
| `severity` | string | For marker color/icon |
| `city` | string \| null | For marker tooltip |
| `credibility_score` | float \| null | For marker opacity/style |
| `verification_status` | string | For marker style |
| `event_timestamp` | ISO 8601 UTC | For marker tooltip |

### PostGIS Spatial Query

```sql
SELECT event_id, latitude, longitude, event_category, severity, city,
       credibility_score, verification_status, event_timestamp
FROM events
WHERE geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
  AND ($5::text IS NULL OR event_category = $5)
  AND ($6::text IS NULL OR severity = $6)
  AND ($7::text IS NULL OR verification_status = $7)
  AND ($8::timestamptz IS NULL OR event_timestamp >= $8)
  AND ($9::timestamptz IS NULL OR event_timestamp <= $9)
  AND ($10::text IS NULL OR city = $10)
ORDER BY event_timestamp DESC
LIMIT 1000;
```

> `ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)` creates the
> bounding box. The `&&` operator uses the GIST spatial index for fast
> intersection. Results are capped at 1000 to prevent map overload.

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `INVALID_COORDINATES` | Bounding box parameters missing or out of range |
| 422 | `VALIDATION_ERROR` | Parameter type mismatch |

---

## 12. Citizen Report API

### `POST /api/v1/citizen-reports`

**Purpose:** Accept citizen-submitted weather reports.

**Authentication:** None (public submission)

**Kafka Integration:** Produces a Canonical Weather Event to `citizen.raw`.
Does **NOT** directly insert into PostgreSQL. The event flows through
Spark → ML → `weather.events` → PostgreSQL writer → PostgreSQL.

### Request Body

```json
{
  "city": "Mumbai",
  "district": "Mumbai City",
  "state": "Maharashtra",
  "latitude": 19.076,
  "longitude": 72.8777,
  "category": "heavy_rainfall",
  "severity": "high",
  "description": "Severe waterlogging near Andheri station. Water level up to knee height.",
  "timestamp": "2026-08-31T10:30:00.000Z"
}
```

### Request Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `city` | string | Yes | Non-empty | City name |
| `district` | string | No | — | District name |
| `state` | string | No | — | State name |
| `latitude` | float | Conditional* | −90 to 90 | WGS-84 decimal degrees |
| `longitude` | float | Conditional* | −180 to 180 | WGS-84 decimal degrees |
| `category` | string (enum) | Yes | Must be in `02_DATA_SCHEMA.md §1.2` | Event category |
| `severity` | string (enum) | No | Must be in `02_DATA_SCHEMA.md §1.3` if provided | Severity level |
| `description` | string | No | Max 2000 chars | Free-text description |
| `timestamp` | ISO 8601 UTC | No | Must not be >5 min in future | When event occurred |
| `photos` | file[] | No | Max 5 files, max 5 MB each | Uploaded images |
| `videos` | file[] | No | Max 2 files, max 20 MB each | Uploaded videos |

> *Location rule (from `02_DATA_SCHEMA.md §3.2`): At least one of
> (`latitude` + `longitude` together) **or** `city` must be provided.*

### Request Content-Type

This endpoint accepts `multipart/form-data` to support file uploads.
All text fields are sent as form fields. Files are sent as multipart files.

### How the API Constructs the Canonical Weather Event

FastAPI transforms the citizen request into a Canonical Weather Event per
`02_DATA_SCHEMA.md §2` and `03_KAFKA_CONTRACT.md §4`:

| Canonical Field | Value |
|----------------|-------|
| `event_id` | `uuid.uuid4()` |
| `source_id` | `"citizen_<uuid.uuid4()>"` |
| `source_type` | `"citizen"` |
| `source_name` | `"citizen_form"` |
| `source_url` | `null` |
| `source_trust_score` | `null` |
| `timestamp` | Request `timestamp` or `datetime.now(timezone.utc)` |
| `ingestion_timestamp` | `datetime.now(timezone.utc)` |
| `location.*` | Mapped from request fields; `country` defaults to `"India"` |
| `event.category` | From request `category` |
| `event.severity` | From request `severity` (nullable) |
| `event.description` | From request `description` (nullable) |
| `social_metadata.*` | All null/empty (not applicable for citizen reports) |
| `media.photos` | URLs of uploaded files (after storage) |
| `media.videos` | URLs of uploaded files (after storage) |
| `ai.*` | All null (ML enrichment happens in Spark) |
| `verification.status` | `"pending"` |
| `verification.verified_by` | `null` |
| `verification.verification_timestamp` | `null` |

### Response — 201 Created

```json
{
  "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "submitted",
  "message": "Citizen report submitted successfully. It will appear on the dashboard shortly after processing.",
  "timestamp": "2026-08-31T10:31:00.000Z"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID v4 | The generated event ID |
| `status` | string | Always `"submitted"` on success |
| `message` | string | Human-readable confirmation |
| `timestamp` | ISO 8601 UTC | Time of submission |

### Processing Flow

```
Citizen → React Form (frontend :5173)
  → POST /api/v1/citizen-reports (api :8000)
  → Pydantic validation + Canonical Event construction
  → Upload media to /data/media/ (if any)
  → Produce to Kafka: citizen.raw
  → Spark validation + ML enrichment
  → Kafka: weather.events
  → PostgreSQL Writer → PostgreSQL
  → GET /events (FastAPI) → Dashboard
```

**Target latency:** ~5 seconds end-to-end under normal demo conditions.

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `MISSING_REQUIRED_FIELD` | `city` or `category` missing |
| 400 | `INVALID_ENUM_VALUE` | `category` not in allowed taxonomy |
| 400 | `INVALID_COORDINATES` | Lat provided without lon or vice versa |
| 400 | `MEDIA_TOO_LARGE` | File exceeds size limit |
| 400 | `MEDIA_INVALID_TYPE` | File type not allowed |
| 409 | `DUPLICATE_REPORT` | Same `source_id` already processed |
| 422 | `VALIDATION_ERROR` | Pydantic model validation failed |
| 503 | `KAFKA_UNAVAILABLE` | Cannot produce to `citizen.raw` |

---

## 13. Citizen Media Upload

### 13.1 Approach

Media uploads are handled via `multipart/form-data` on the citizen report endpoint.
Files are saved to the local filesystem under `/data/media/` and their URLs are
referenced in the Canonical Weather Event's `media.photos` and `media.videos` fields.

### 13.2 Storage Path

```
/data/media/
├── photos/
│   └── YYYY-MM-DD/
│       └── <uuid>.<ext>
└── videos/
    └── YYYY-MM-DD/
        └── <uuid>.<ext>
```

### 13.3 Constraints

| Constraint | Value |
|-----------|-------|
| Max image file size | 5 MB per file |
| Max video file size | 20 MB per file |
| Max images per report | 5 |
| Max videos per report | 2 |
| Allowed image types | `.jpg`, `.jpeg`, `.png`, `.webp` |
| Allowed video types | `.mp4`, `.webm` |
| Filename format | `<uuid-v4>.<original-extension>` (sanitised) |
| Executable files | **Blocked** — no `.exe`, `.sh`, `.bat`, `.ps1`, `.php`, `.js` |
| Path traversal | **Blocked** — filenames sanitised; no `..`, `/`, `\` |

### 13.4 Filename Sanitisation

1. Original filename is **discarded**.
2. A new UUID v4 is generated.
3. The original extension is extracted, lowercased, and validated against the allowlist.
4. Final filename: `<uuid>.<validated-ext>`.

### 13.5 Public URL

Uploaded files are served via FastAPI static file mounting:
```
GET /media/photos/YYYY-MM-DD/<uuid>.jpg
GET /media/videos/YYYY-MM-DD/<uuid>.mp4
```

The Canonical Weather Event's `media.photos` / `media.videos` fields contain
these public URLs.

### 13.6 Failure Behavior

- If file storage fails (disk full, permissions): return `500 INTERNAL_ERROR`.
  The citizen report is **not** submitted. The citizen should retry.
- If individual file validation fails (wrong type, too large): return
  `400 MEDIA_TOO_LARGE` or `400 MEDIA_INVALID_TYPE` with details.
- If some files succeed and one fails: **reject the entire request**
  (atomic — no partial uploads).

---

## 14. Verification API

### `POST /api/v1/verification`

**Purpose:** Admin verification action on an event.

**Authentication:** **Required** (JWT Bearer token)

**Kafka Integration:** After updating PostgreSQL, produces a `verification_action`
message to `weather.verified` per `03_KAFKA_CONTRACT.md §6`.

### Request Body

```json
{
  "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "action": "verified",
  "notes": "Confirmed by administrator after cross-referencing with IMD data."
}
```

### Request Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `event_id` | UUID v4 | Yes | Must be valid UUID; event must exist | Event to verify |
| `action` | string (enum) | Yes | Must be one of the values below | Verification action |
| `notes` | string | No | Max 1000 chars | Admin notes |

### Allowed Actions

| `action` Value | `verification_status` Set To | Description |
|----------------|------------------------------|-------------|
| `"verified"` | `"verified"` | Admin confirms event is genuine |
| `"rejected"` | `"pending"` | Admin rejects event (returned to pending for further review) |
| `"marked_suspicious"` | `"suspicious"` | Admin flags event as suspicious |
| `"marked_duplicate"` | `"duplicate"` | Admin identifies event as duplicate |

> These actions and status values are consistent with
> `02_DATA_SCHEMA.md §1.4` and `03_KAFKA_CONTRACT.md §6.3`.

### Response — 200 OK

```json
{
  "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "action": "verified",
  "previous_status": "pending",
  "new_status": "verified",
  "performed_by": "admin_01",
  "performed_at": "2026-08-31T14:30:00.000Z",
  "message": "Event verified successfully"
}
```

### Server-Side Processing (Transaction)

1. **Authenticate:** Validate JWT token; extract `username` as `performed_by`.
2. **Validate event exists:** `SELECT verification_status FROM events WHERE event_id = $1`.
   Return 404 if not found.
3. **Begin transaction:**
   a. `UPDATE events SET verification_status = $new_status, verified_by = $performed_by,
       verification_timestamp = NOW() WHERE event_id = $1`
   b. `INSERT INTO verification_log (event_id, action, performed_by, notes, performed_at)
       VALUES ($1, $action, $performed_by, $notes, NOW())`
4. **Commit transaction.**
5. **Produce to Kafka:** Send `verification_action` message to `weather.verified`
   per `03_KAFKA_CONTRACT.md §6.1`.
6. **Return response.**

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |
| 400 | `INVALID_ENUM_VALUE` | `action` not in allowed values |
| 400 | `MISSING_REQUIRED_FIELD` | `event_id` or `action` missing |
| 404 | `EVENT_NOT_FOUND` | Event with given ID does not exist |
| 500 | `INTERNAL_ERROR` | Database transaction failure |
| 503 | `KAFKA_UNAVAILABLE` | PostgreSQL updated but Kafka produce failed (see note) |

> **Kafka failure note:** If PostgreSQL commit succeeds but Kafka produce fails,
> the API logs a warning and returns `200 OK` to the admin. The database change
> is authoritative; the Kafka `weather.verified` message is an audit trail.
> A background retry queue (or manual replay) handles the missed message.
> This avoids blocking admin actions on Kafka availability.

---

## 15. Authentication Endpoint

### `POST /api/v1/auth/login`

**Purpose:** Admin login to obtain JWT token.

**Authentication:** None (this endpoint is the login itself)

### Request Body

```json
{
  "username": "admin",
  "password": "secure_password_here"
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Admin username |
| `password` | string | Yes | Admin password |

### Response — 200 OK

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800,
  "username": "admin"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT token |
| `token_type` | string | Always `"bearer"` |
| `expires_in` | integer | Token lifetime in seconds (default: 28800 = 8 hours) |
| `username` | string | Authenticated username |

### Token Usage

Include in subsequent requests to protected endpoints:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Error Cases

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `MISSING_REQUIRED_FIELD` | `username` or `password` missing |
| 401 | `UNAUTHORIZED` | Invalid credentials |

### Security Notes

- Credentials are compared against `ADMIN_USERNAME` and `ADMIN_PASSWORD`
  (bcrypt hash) loaded from environment variables.
- No brute-force protection in MVP beyond standard logging.
- Failed login attempts are logged with the requesting IP address.
- Token is stateless (no server-side session); revocation requires
  `JWT_SECRET_KEY` rotation (restart all services).

---

## 16. Response Models (Pydantic Schemas)

### 16.1 EventResponse (Detail View)

```python
class EventSource(BaseModel):
    source_id: str
    source_type: str          # Literal of 02_DATA_SCHEMA.md §1.1
    source_name: str
    source_url: str | None = None
    source_trust_score: float | None = None

class EventLocation(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str = "India"

class EventClassification(BaseModel):
    category: str             # Literal of 02_DATA_SCHEMA.md §1.2
    severity: str | None = None  # Literal of 02_DATA_SCHEMA.md §1.3
    description: str | None = None

class SocialMetadata(BaseModel):
    hashtags: list[str] = []
    author_id: str | None = None
    platform: str | None = None

class MediaInfo(BaseModel):
    photo_urls: list[str] = []
    video_urls: list[str] = []

class AIInfo(BaseModel):
    classified_category: str | None = None
    classification_confidence: float | None = None
    duplicate_score: float | None = None
    credibility_score: float | None = None
    credibility_reasons: list[str] = []
    cluster_id: str | None = None

class VerificationInfo(BaseModel):
    status: str               # Literal of 02_DATA_SCHEMA.md §1.4
    verified_by: str | None = None
    verification_timestamp: str | None = None
    history: list[VerificationLogEntry] = []

class EventResponse(BaseModel):
    event_id: str
    source: EventSource
    event_timestamp: str
    ingestion_timestamp: str
    location: EventLocation
    event: EventClassification
    social_metadata: SocialMetadata
    media: MediaInfo
    ai: AIInfo
    verification: VerificationInfo
    created_at: str
    updated_at: str
```

### 16.2 EventListItem (List View)

```python
class EventListItem(BaseModel):
    event_id: str
    source_type: str
    source_name: str
    event_timestamp: str
    event_category: str
    severity: str | None = None
    description: str | None = None  # Truncated to 200 chars
    city: str | None = None
    state: str | None = None
    country: str
    latitude: float | None = None
    longitude: float | None = None
    classified_category: str | None = None
    classification_confidence: float | None = None
    credibility_score: float | None = None
    duplicate_score: float | None = None
    verification_status: str
    cluster_id: str | None = None
    created_at: str
```

### 16.3 EventListResponse

```python
class EventListResponse(BaseModel):
    items: list[EventListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
```

### 16.4 MapEventResponse

```python
class MapEvent(BaseModel):
    event_id: str
    latitude: float
    longitude: float
    event_category: str
    severity: str | None = None
    city: str | None = None
    credibility_score: float | None = None
    verification_status: str
    event_timestamp: str

class MapEventResponse(BaseModel):
    events: list[MapEvent]
    count: int
    bbox: dict
```

### 16.5 CitizenReportRequest

```python
class CitizenReportRequest(BaseModel):
    city: str                           # Required
    district: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    category: str                       # Required; 02_DATA_SCHEMA.md §1.2 enum
    severity: str | None = None         # 02_DATA_SCHEMA.md §1.3 enum
    description: str | None = None
    timestamp: str | None = None        # ISO 8601 UTC
```

### 16.6 CitizenReportResponse

```python
class CitizenReportResponse(BaseModel):
    event_id: str
    status: str = "submitted"
    message: str
    timestamp: str
```

### 16.7 VerificationRequest

```python
class VerificationRequest(BaseModel):
    event_id: str                       # Required; UUID v4
    action: str                         # Required; 02_DATA_SCHEMA.md §1.4 action enum
    notes: str | None = None
```

### 16.8 VerificationResponse

```python
class VerificationResponse(BaseModel):
    event_id: str
    action: str
    previous_status: str
    new_status: str
    performed_by: str
    performed_at: str
    message: str
```

### 16.9 HealthResponse

```python
class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    database: Literal["connected", "unavailable"]
    kafka: Literal["connected", "unavailable"]
    timestamp: str
```

### 16.10 LoginRequest / TokenResponse

```python
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str
```

### 16.11 ErrorResponse

```python
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None
    timestamp: str

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

---

## 17. API → Database Mapping

| API Endpoint | Database Operation | Tables |
|--------------|-------------------|--------|
| `GET /events` | `SELECT` with `WHERE` filters, `ORDER BY`, `LIMIT/OFFSET` | `events` |
| `GET /events/{id}` | `SELECT` by `event_id` + `JOIN` verification_log | `events`, `verification_log` |
| `GET /events/stats` | `SELECT COUNT(*)`, `GROUP BY` aggregations | `events` |
| `GET /events/map` | PostGIS spatial query: `ST_MakeEnvelope` + `&&` operator | `events` (GIST index) |
| `POST /citizen-reports` | **No direct DB write** — produces to Kafka `citizen.raw`; event reaches DB via Spark → PostgreSQL writer pipeline | — |
| `POST /verification` | `UPDATE events SET ...` + `INSERT INTO verification_log` (transactional) | `events`, `verification_log` |
| `GET /health` | `SELECT 1` (ping) | — |

### 17.1 Important: Citizen Reports Do NOT Bypass Kafka

Per `01_ARCHITECTURE.md §4`, citizen reports **must** flow through the
full pipeline:

```
FastAPI → citizen.raw → Spark (validate + ML) → weather.events → PostgreSQL writer → PostgreSQL
```

The API does **NOT** insert directly into the `events` table for citizen reports.
Direct insertion would bypass Spark validation and ML enrichment, violating the
architecture.

---

## 18. API → Kafka Mapping

| API Action | Kafka Topic | Message Type | Producer ID |
|-----------|------------|--------------|-------------|
| `POST /citizen-reports` | `citizen.raw` | `weather_event` | `"api"` |
| `POST /verification` | `weather.verified` | `verification_action` | `"api"` |

### 18.1 Kafka Integration Rules

1. **FastAPI does NOT consume** `weather.raw`, `citizen.raw`, `social.raw`, or
   `government.raw` — Spark consumes those.
2. **FastAPI does NOT perform** Spark processing or ML enrichment.
3. **FastAPI does NOT call** ML modules — ML runs inside Spark only.
4. **PostgreSQL is downstream** of `weather.events` — the API reads from
   PostgreSQL; it does not write events (except verification updates).
5. Messages are wrapped in the Kafka envelope per `03_KAFKA_CONTRACT.md §3`.

### 18.2 Citizen Report → Kafka Message

```json
{
  "schema_version": "1.0",
  "message_id": "<uuid-v4>",
  "event_type": "weather_event",
  "produced_at": "2026-08-31T10:31:00.000Z",
  "producer": "api",
  "payload": {
    "event_id": "<uuid-v4>",
    "source_id": "citizen_<uuid-v4>",
    "source_type": "citizen",
    "source_name": "citizen_form",
    "...": "Complete Canonical Weather Event per 02_DATA_SCHEMA.md §2"
  }
}
```

### 18.3 Verification → Kafka Message

Per `03_KAFKA_CONTRACT.md §6.1`:

```json
{
  "schema_version": "1.0",
  "message_id": "<uuid-v4>",
  "event_type": "verification_action",
  "produced_at": "2026-08-31T14:30:00.000Z",
  "producer": "api",
  "payload": {
    "event_id": "<uuid-v4>",
    "action": "verified",
    "performed_by": "admin_01",
    "notes": "Confirmed by administrator",
    "previous_status": "pending",
    "new_status": "verified",
    "performed_at": "2026-08-31T14:30:00.000Z"
  }
}
```

---

## 19. API → Frontend Mapping

| Frontend Feature | API Endpoint | HTTP Method | Auth | Notes |
|-----------------|-------------|-------------|------|-------|
| Dashboard KPIs | `/api/v1/events/stats` | GET | No | Refreshed every 30 seconds |
| Event list (table) | `/api/v1/events` | GET | No | Paginated, filterable |
| Event map | `/api/v1/events/map` | GET | No | Bounding box from Leaflet |
| Event detail | `/api/v1/events/{event_id}` | GET | No | Full detail + verification history |
| Citizen form | `/api/v1/citizen-reports` | POST | No | Multipart form data |
| Admin login | `/api/v1/auth/login` | POST | No | Returns JWT |
| Admin verify/reject | `/api/v1/verification` | POST | JWT | Protected endpoint |
| System status | `/api/v1/health` | GET | No | Polled every 10 seconds |

### 19.1 Frontend Port Configuration

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite dev) | 5173 | `http://localhost:5173` |
| API (FastAPI) | 8000 | `http://localhost:8000/api/v1` |
| API docs | 8000 | `http://localhost:8000/docs` |

---

## 20. CORS

### 20.1 Development Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 20.2 Configuration via Environment Variables

```
CORS_ORIGINS=http://localhost:5173    # Comma-separated list of allowed origins
```

### 20.3 Rules

- **No unrestricted `*` origin** in any configuration.
- Only explicitly configured origins are allowed.
- `allow_credentials=True` to support cookie-based auth if needed in future.
- `Authorization` header is explicitly allowed for JWT Bearer tokens.

---

## 21. Rate Limiting / Abuse Protection

**MVP-simple, in-memory approach.** No Redis (out of scope per `01_ARCHITECTURE.md §16`).

### 21.1 Limits

| Endpoint | Limit | Window | Behavior |
|----------|-------|--------|----------|
| `POST /citizen-reports` | 10 requests | per IP per minute | 429 Too Many Requests |
| `POST /auth/login` | 5 attempts | per IP per minute | 429 Too Many Requests |
| `POST /verification` | 30 requests | per user per minute | 429 Too Many Requests |
| All GET endpoints | No limit | — | No rate limiting for reads |

### 21.2 Implementation Notes

- In-memory dictionary with sliding window counter per IP/user.
- **Lost on API restart** — acceptable for MVP.
- Logs rate-limited requests with IP address for monitoring.
- Response includes `Retry-After` header (seconds until next allowed request).

### 21.3 Response — 429 Too Many Requests

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please retry after 30 seconds.",
    "details": {
      "retry_after": 30
    },
    "timestamp": "2026-08-31T14:30:00.000Z"
  }
}
```

---

## 22. Security Requirements

| Requirement | Implementation |
|------------|---------------|
| Pydantic validation | All request bodies validated via Pydantic v2 models |
| JWT for admin | Bearer token required on `POST /verification` |
| Environment variables | All secrets (`JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, `KAFKA_BOOTSTRAP_SERVERS`) from `.env` |
| No hardcoded credentials | `.env` gitignored; `.env.example` committed without values |
| No secrets in Kafka messages | Canonical Weather Event contains no API keys or tokens |
| No unnecessary PII | Citizen reports store only event-relevant data (location, description) |
| Media validation | File type, size, and filename sanitisation before storage |
| CORS restrictions | Only configured origins allowed; no `*` |
| SQL injection protection | Parameterised queries via SQLAlchemy/psycopg2; no raw string interpolation |
| Authentication on admin endpoints | `POST /verification` requires valid JWT |
| Filesystem security | Media paths sanitised; no path traversal; no executable uploads |

### 22.1 .env.example (Committed Without Values)

```
# Database
DATABASE_URL=

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Authentication
JWT_SECRET_KEY=
JWT_EXPIRATION_HOURS=8
ADMIN_USERNAME=admin
ADMIN_PASSWORD=

# CORS
CORS_ORIGINS=http://localhost:5173

# Media
MEDIA_MAX_IMAGE_SIZE_MB=5
MEDIA_MAX_VIDEO_SIZE_MB=20
```

---

## 23. Near-Real-Time Behavior

### 23.1 Expected Flow Timing

```
Citizen submission
      ↓ (~0.1s)    Pydantic validation + Kafka produce
citizen.raw
      ↓ (~1-3s)    Spark micro-batch (depends on trigger interval)
weather.events
      ↓ (~0.5s)    PostgreSQL writer consume + upsert
PostgreSQL
      ↓ (~0.1s)    GET /events query
Dashboard update
```

**Target total latency:** ~5 seconds under normal demo conditions.

### 23.2 Guarantees

- **Not** sub-second real-time. The system is near-real-time.
- Latency depends on Spark micro-batch trigger interval (configurable).
- Under heavy load, latency may increase. The system degrades gracefully.
- The `POST /citizen-reports` endpoint returns `201` immediately upon
  Kafka produce success — it does **not** wait for the event to appear
  in the database.

### 23.3 Frontend Polling

The React dashboard polls `GET /events/stats` every 30 seconds to refresh
KPIs. The event list page can be manually refreshed or auto-refreshed
every 10 seconds.

---

## 24. Failure Handling

| # | Failure | HTTP Status | Response | Logging | Retry |
|---|---------|------------|----------|---------|-------|
| 1 | **Database unavailable** (read endpoints) | 503 | `DATABASE_UNAVAILABLE` error | ERROR log with connection details | Client retries after 5s |
| 2 | **Database unavailable** (health check) | 503 | `"database": "unavailable"` | WARNING log | Docker healthcheck retries |
| 3 | **Kafka unavailable** (citizen report) | 503 | `KAFKA_UNAVAILABLE` error | ERROR log | Client retries |
| 4 | **Kafka unavailable** (verification) | 200* | Response sent; Kafka retry in background | WARNING log (Kafka is audit-only) | Background retry |
| 5 | **Invalid citizen request** | 400/422 | Validation error with field details | INFO log | Client corrects and resubmits |
| 6 | **Invalid event ID format** | 400 | `INVALID_UUID` error | INFO log | Client corrects |
| 7 | **Event not found** | 404 | `EVENT_NOT_FOUND` error | INFO log | N/A |
| 8 | **Invalid verification action** | 400 | `INVALID_ENUM_VALUE` error | INFO log | Client corrects |
| 9 | **Unauthorized admin** | 401 | `UNAUTHORIZED` error | WARNING log with IP | Client logs in again |
| 10 | **Expired JWT** | 401 | `TOKEN_EXPIRED` error | INFO log | Client re-authenticates |
| 11 | **Media upload failure** | 400/500 | Specific error | ERROR log | Client retries |
| 12 | **Malformed JSON** | 400 | `INVALID_JSON` error | INFO log | Client fixes request |
| 13 | **Database transaction failure** (verification) | 500 | `INTERNAL_ERROR` error | ERROR log with stack trace | Client retries |

> *Note on #4: Verification updates PostgreSQL first (transactional). If
> PostgreSQL commit succeeds but Kafka produce fails, the API returns `200 OK`
> because the database is the authoritative source. The Kafka message is
> supplementary audit trail.

---

## 25. API Documentation

FastAPI automatically generates interactive API documentation:

| URL | Format | Purpose |
|-----|--------|---------|
| `http://localhost:8000/docs` | Swagger UI | Interactive API explorer; test endpoints directly |
| `http://localhost:8000/redoc` | ReDoc | Readable API reference documentation |
| `http://localhost:8000/openapi.json` | OpenAPI 3.1 JSON | Machine-readable API schema |

These are development/demo endpoints. In production, they can be disabled
via configuration.

---

## 26. Implementation Checklist (M5)

### Project Structure

- [ ] `services/api/` directory with `main.py`, `routers/`, `models/`, `services/`, `config/`
- [ ] `requirements.txt` with: `fastapi`, `uvicorn`, `pydantic`, `psycopg2-binary`, `sqlalchemy`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`, `confluent-kafka`
- [ ] `.env` and `.env.example` files

### Pydantic Models

- [ ] `EventResponse`, `EventListItem`, `EventListResponse`
- [ ] `MapEvent`, `MapEventResponse`
- [ ] `CitizenReportRequest`, `CitizenReportResponse`
- [ ] `VerificationRequest`, `VerificationResponse`
- [ ] `HealthResponse`
- [ ] `LoginRequest`, `TokenResponse`
- [ ] `ErrorResponse`

### Database Connection

- [ ] SQLAlchemy engine configured from `DATABASE_URL`
- [ ] Connection pool with appropriate `pool_size` and `max_overflow`
- [ ] Session dependency for FastAPI endpoints

### SQL / PostGIS Queries

- [ ] `GET /events`: Parameterised SELECT with dynamic WHERE, ORDER BY, LIMIT/OFFSET
- [ ] `GET /events/{id}`: SELECT by event_id + JOIN verification_log
- [ ] `GET /events/stats`: GROUP BY aggregations for all category/severity/status/city/source breakdowns
- [ ] `GET /events/map`: PostGIS `ST_MakeEnvelope` + `&&` spatial query with GIST index

### Event Endpoints

- [ ] `GET /events` with all filters and pagination
- [ ] `GET /events/{event_id}` with nested response structure
- [ ] `GET /events/stats` with all aggregation groups
- [ ] `GET /events/map` with bounding box and spatial query

### Citizen Endpoint

- [ ] `POST /citizen-reports` with multipart form handling
- [ ] Canonical Weather Event construction per `02_DATA_SCHEMA.md §2`
- [ ] Media upload to `/data/media/` with validation
- [ ] Kafka produce to `citizen.raw` with envelope wrapping

### Verification Endpoint

- [ ] `POST /verification` with JWT authentication
- [ ] Transactional PostgreSQL update (events + verification_log)
- [ ] Kafka produce to `weather.verified` with verification_action payload
- [ ] Proper error handling for Kafka failure (non-blocking)

### Authentication

- [ ] JWT token generation on `/auth/login`
- [ ] JWT token validation middleware/dependency
- [ ] `ADMIN_USERNAME` and `ADMIN_PASSWORD` from environment
- [ ] Bcrypt password comparison

### Kafka Producer

- [ ] `confluent-kafka` Producer configured with `KAFKA_BOOTSTRAP_SERVERS`
- [ ] Envelope wrapper function (schema_version, message_id, event_type, produced_at, producer, payload)
- [ ] Citizen report produce to `citizen.raw`
- [ ] Verification produce to `weather.verified`

### CORS

- [ ] CORS middleware configured with `CORS_ORIGINS` from environment
- [ ] Allow `Authorization` and `Content-Type` headers

### Error Handling

- [ ] Global exception handler returning consistent `ErrorResponse`
- [ ] Pydantic validation error handler (422 → structured error)
- [ ] Database error handler (connection failures → 503)
- [ ] Kafka error handler (produce failures → 503 or logged warning)

### Health Checks

- [ ] `GET /health` with PostgreSQL ping and Kafka connectivity check
- [ ] Docker healthcheck configuration

### Tests

- [ ] Unit tests for Pydantic models (valid/invalid inputs)
- [ ] Integration tests for GET endpoints (mocked database)
- [ ] Integration test for citizen report (mocked Kafka)
- [ ] Integration test for verification (mocked database + Kafka)
- [ ] Auth flow test (login → token → protected endpoint)

### Environment Configuration

- [ ] All environment variables documented in `.env.example`
- [ ] Application refuses to start without `JWT_SECRET_KEY`
- [ ] Application refuses to start without `DATABASE_URL`

---

## 27. Cross-Contract Validation

### 27.1 Against `01_ARCHITECTURE.md`

| Check | Result | Evidence |
|-------|--------|----------|
| Port 8000 | ✅ PASS | Architecture §5: `api` service on port 8000; this doc defines port 8000 |
| Listed endpoints match | ✅ PASS | Architecture §3 diagram lists: GET /events, GET /events/{id}, GET /events/stats, GET /events/map, POST /citizen-reports, POST /verification, GET /health — all defined in this doc |
| Citizen flow | ✅ PASS | Architecture §4: `POST /citizen-reports → citizen.raw → Spark → weather.events → PostgreSQL` — this doc §12 follows exactly |
| Verification flow | ✅ PASS | Architecture §9: `POST /verification → PostgreSQL + weather.verified` — this doc §14 follows exactly |
| PostgreSQL/PostGIS | ✅ PASS | Read endpoints query PostgreSQL; PostGIS used for `/events/map` — consistent with architecture §3 diagram |
| Kafka integration | ✅ PASS | API produces to `citizen.raw` and `weather.verified` only — consistent with architecture §9 topic registry |
| React port 5173 | ✅ PASS | CORS configured for `localhost:5173`; architecture §5 defines frontend on 5173 |
| Authentication | ✅ PASS | Architecture §12: "Admin actions require authentication (mechanism defined in `04_API_CONTRACT.md`)" — this doc resolves as JWT; architecture open question #3 is resolved |

### 27.2 Against `02_DATA_SCHEMA.md`

| Check | Result | Evidence |
|-------|--------|----------|
| Event fields | ✅ PASS | All fields in list/detail responses map to `events` table columns defined in schema §6.1 |
| Source type enum | ✅ PASS | `"citizen"` used for citizen reports — matches schema §1.1 |
| Event category enum | ✅ PASS | Category validation on citizen report uses schema §1.2 values exactly |
| Severity enum | ✅ PASS | Severity validation uses schema §1.3 values: `low`, `moderate`, `high`, `extreme` |
| Verification status enum | ✅ PASS | Actions set status values matching schema §1.4: `pending`, `verified`, `needs_review`, `suspicious`, `duplicate` |
| Location fields | ✅ PASS | Location rule (paired lat/lon or city) enforced per schema §3.2 |
| Timestamp format | ✅ PASS | ISO 8601 UTC used throughout, per schema §4 |
| UUID format | ✅ PASS | UUID v4 used for event_id, consistent with schema §5 |
| Verification log table | ✅ PASS | Detail view joins `verification_log` table per schema §6.5 |
| JSON→DB mapping | ✅ PASS | Detail response restructures flat DB columns to nested JSON per schema §6 preamble |

### 27.3 Against `03_KAFKA_CONTRACT.md`

| Check | Result | Evidence |
|-------|--------|----------|
| `citizen.raw` topic name | ✅ PASS | Citizen report produces to `citizen.raw` — matches contract §2.2 |
| `weather.verified` topic name | ✅ PASS | Verification produces to `weather.verified` — matches contract §2.2 |
| Message envelope format | ✅ PASS | Both Kafka messages use envelope per contract §3.1 (schema_version, message_id, event_type, produced_at, producer, payload) |
| Verification action structure | ✅ PASS | Verification payload matches contract §6.1 (event_id, action, performed_by, notes, previous_status, new_status, performed_at) |
| Verification actions | ✅ PASS | `verified`, `rejected`, `marked_suspicious`, `marked_duplicate` — matches contract §6.3 |
| Producer responsibility | ✅ PASS | API is the producer for `citizen.raw` and `weather.verified` — matches contract §2.1 |
| Event type values | ✅ PASS | `"weather_event"` for citizen reports, `"verification_action"` for verification — matches contract §3.3 |
| No direct DB insert for citizen reports | ✅ PASS | Citizen reports flow through Kafka → Spark → PostgreSQL writer — consistent with contract §15.2 |

### 27.4 Summary

| Contract | Result |
|----------|--------|
| `01_ARCHITECTURE.md` | ✅ PASS — no conflicts found |
| `02_DATA_SCHEMA.md` | ✅ PASS — no conflicts found |
| `03_KAFKA_CONTRACT.md` | ✅ PASS — no conflicts found |

---

## 28. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | ~~FastAPI auth mechanism for Admin Panel~~ | M5 | ✅ **Resolved** — JWT Bearer token authentication per §3 of this document |
| 2 | Admin user seed data — how are initial admin credentials created? | M5 | Open —建議: seed via init script or first-run setup |
| 3 | Media file serving — FastAPI static mount or separate nginx? | M5 | Open for MVP: FastAPI static mount per §13.5 |
| 4 | Event list pagination — should `total` count use `COUNT(*)` or `approx_count` for large datasets? | M5 | Open for MVP: exact `COUNT(*)` (acceptable at hackathon scale) |

---

## 29. Final Approval Statement

> This document is the API contract source of truth. Any change to endpoint
> names, HTTP methods, request/response schemas, authentication behavior,
> status codes, or API-to-Kafka/database integration must be reflected here
> before implementation.

---

## Appendix A: Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `KAFKA_BOOTSTRAP_SERVERS` | Yes | `kafka:9092` | Kafka broker addresses |
| `JWT_SECRET_KEY` | Yes | — | Secret for JWT signing (app refuses to start without) |
| `JWT_EXPIRATION_HOURS` | No | `8` | Token lifetime in hours |
| `ADMIN_USERNAME` | Yes | `admin` | Admin login username |
| `ADMIN_PASSWORD` | Yes | — | Admin password (bcrypt hash) |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed origins |
| `MEDIA_MAX_IMAGE_SIZE_MB` | No | `5` | Max image upload size |
| `MEDIA_MAX_VIDEO_SIZE_MB` | No | `20` | Max video upload size |
| `APP_ENV` | No | `development` | `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-09-01 | Initial API contract. Resolves architecture open question #3 (auth mechanism → JWT). Defines all 8 endpoints, Pydantic models, Kafka integration, error handling, and cross-contract validation. |
