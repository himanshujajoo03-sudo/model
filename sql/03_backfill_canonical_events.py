#!/usr/bin/env python3
"""
SIH26069 — Backfill Canonical Events
Consolidates existing source records in the events table into canonical_events.

Uses the same matching logic as pg_writer:
- Same event_category
- Geographic distance <= 50km
- Temporal distance <= 24 hours

Run: python sql/03_backfill_canonical_events.py
"""

import os
import sys
import uuid
import math
import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://weather:weather@localhost:5432/weatherdb",
)

MATCH_DISTANCE_KM = 50.0
MATCH_TIME_HOURS = 24.0

SEV_ORDER = {"low": 0, "moderate": 1, "high": 2, "extreme": 3}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def find_matching_canonical(conn, event):
    """Find existing canonical event matching this source record."""
    cur = conn.cursor()
    cur.execute("""
        SELECT canonical_event_id, latitude, longitude, last_seen
        FROM canonical_events
        WHERE event_category = %s
          AND last_seen >= %s - INTERVAL '%s hours'
          AND last_seen <= %s + INTERVAL '%s hours'
    """, (
        event["event_category"],
        event["event_timestamp"], MATCH_TIME_HOURS,
        event["event_timestamp"], MATCH_TIME_HOURS,
    ))

    for row in cur.fetchall():
        ce_id, ce_lat, ce_lon, _ = row
        if ce_lat is None or ce_lon is None:
            continue
        dist = haversine_km(
            float(event["latitude"]), float(event["longitude"]),
            float(ce_lat), float(ce_lon),
        )
        if dist <= MATCH_DISTANCE_KM:
            return str(ce_id)
    return None


def upsert_canonical(conn, event, existing_ce_id):
    """Create or update a canonical event."""
    cur = conn.cursor()
    sev = event.get("severity")
    cred = event.get("credibility_score")
    conf = event.get("classification_confidence")
    source_name = event.get("source_name")
    event_ts = event["event_timestamp"]

    if existing_ce_id:
        cur.execute("""
            UPDATE canonical_events SET
                last_seen = GREATEST(last_seen, %s),
                report_count = report_count + 1,
                contributing_sources = (
                    CASE WHEN %s = ANY(contributing_sources)
                         THEN contributing_sources
                         ELSE array_append(contributing_sources, %s)
                    END
                ),
                source_count = (
                    SELECT COUNT(DISTINCT unnest)
                    FROM unnest(
                        CASE WHEN %s = ANY(contributing_sources)
                             THEN contributing_sources
                             ELSE array_append(contributing_sources, %s)
                        END
                    )
                ),
                severity = CASE
                    WHEN %s IS NULL THEN severity
                    WHEN severity IS NULL THEN %s
                    WHEN %s::text > severity THEN %s
                    ELSE severity
                END,
                credibility_score = CASE
                    WHEN %s IS NULL THEN credibility_score
                    WHEN credibility_score IS NULL THEN %s
                    WHEN %s > credibility_score THEN %s
                    ELSE credibility_score
                END,
                classification_confidence = CASE
                    WHEN %s IS NULL THEN classification_confidence
                    WHEN classification_confidence IS NULL THEN %s
                    WHEN %s > classification_confidence THEN %s
                    ELSE classification_confidence
                END
            WHERE canonical_event_id = %s
            RETURNING canonical_event_id
        """, (
            event_ts,
            source_name, source_name,
            source_name, source_name,
            sev, sev, sev, sev,
            cred, cred, cred, cred,
            conf, conf, conf, conf,
            existing_ce_id,
        ))
        result = cur.fetchone()
        if result:
            return str(result[0])
        return None
    else:
        ce_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO canonical_events (
                canonical_event_id, event_category, severity, description,
                latitude, longitude, city, district, state, country,
                first_seen, last_seen, source_count, report_count,
                contributing_sources,
                classified_category, classification_confidence,
                credibility_score, credibility_reasons,
                verification_status
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, 1, 1,
                ARRAY[%s],
                %s, %s,
                %s, %s,
                %s
            )
            RETURNING canonical_event_id
        """, (
            ce_id,
            event["event_category"], sev,
            event.get("description"),
            event["latitude"], event["longitude"],
            event.get("city"), event.get("district"),
            event.get("state"), event.get("country", "India"),
            event_ts, event_ts,
            source_name,
            event.get("classified_category"),
            conf, cred,
            event.get("credibility_reasons") or [],
            event.get("verification_status") or "pending",
        ))
        result = cur.fetchone()
        return str(result[0]) if result else None


def backfill():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        # Fetch all source records ordered by timestamp
        cur = conn.cursor()
        cur.execute("""
            SELECT event_id, source_id, source_type, source_name,
                   event_timestamp, event_category, severity, description,
                   latitude, longitude, city, district, state, country,
                   classified_category, classification_confidence,
                   credibility_score, credibility_reasons,
                   verification_status
            FROM events
            ORDER BY event_timestamp ASC
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} source records to backfill")

        canonical_map = {}  # source_record_id → canonical_event_id
        created = 0
        matched = 0

        for row in rows:
            event = {
                "event_id": str(row[0]),
                "source_id": row[1],
                "source_type": row[2],
                "source_name": row[3],
                "event_timestamp": row[4],
                "event_category": row[5],
                "severity": row[6],
                "description": row[7],
                "latitude": float(row[8]) if row[8] else None,
                "longitude": float(row[9]) if row[9] else None,
                "city": row[10],
                "district": row[11],
                "state": row[12],
                "country": row[13],
                "classified_category": row[14],
                "classification_confidence": float(row[15]) if row[15] else None,
                "credibility_score": float(row[16]) if row[16] else None,
                "credibility_reasons": row[17] or [],
                "verification_status": row[18] or "pending",
            }

            # Find matching canonical event
            existing_ce = find_matching_canonical(conn, event)
            if existing_ce:
                ce_id = upsert_canonical(conn, event, existing_ce)
                matched += 1
            else:
                ce_id = upsert_canonical(conn, event, None)
                created += 1

            if ce_id:
                canonical_map[event["event_id"]] = ce_id

        # Update source records with their canonical_event_id
        cur.execute("SELECT canonical_event_id IS NOT NULL FROM events LIMIT 1")
        has_col = cur.fetchone() is not None

        if has_col:
            for event_id, ce_id in canonical_map.items():
                cur.execute(
                    "UPDATE events SET canonical_event_id = %s WHERE event_id = %s",
                    (ce_id, event_id),
                )

        conn.commit()

        # Report results
        print(f"\n=== BACKFILL RESULTS ===")
        print(f"Source records processed: {len(rows)}")
        print(f"New canonical events created: {created}")
        print(f"Existing canonical events matched: {matched}")

        # Count canonical events
        cur.execute("SELECT COUNT(*) FROM canonical_events")
        ce_count = cur.fetchone()[0]
        print(f"Total canonical events: {ce_count}")

        # Distribution
        cur.execute("""
            SELECT ce.canonical_event_id, ce.event_category, ce.city,
                   ce.source_count, ce.report_count
            FROM canonical_events ce
            ORDER BY ce.first_seen
        """)
        print(f"\nCanonical event distribution:")
        for r in cur.fetchall():
            print(f"  {r[1]}/{r[2]} — sources: {r[3]}, reports: {r[4]}")

        return 0

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(backfill())
