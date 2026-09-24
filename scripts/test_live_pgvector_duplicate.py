"""
SIH26069 — Live Verification Test for Semantic pgvector Duplicate Detection
Inserts two paraphrased but semantically identical events into the live pipeline
and validates that pgvector <=> cosine similarity query influences the duplicate
score in PostgreSQL.
"""

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta


def psql_query_json(sql: str):
    """Execute a query in PostgreSQL and parse rows as dicts via row_to_json."""
    wrapped_sql = f"SELECT row_to_json(t) FROM ({sql}) t;"
    cmd = [
        "docker", "exec", "weather-postgres",
        "psql", "-U", "weather", "-d", "weatherdb",
        "-t", "-A", "-c", wrapped_sql
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"psql error: {res.stderr}")
    out = res.stdout.strip()
    if not out:
        return []
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def publish_kafka_envelope(envelope: dict):
    """Publish envelope line to Kafka weather.events topic via docker exec."""
    line = json.dumps(envelope)
    cmd = [
        "docker", "exec", "-i", "weather-kafka",
        "kafka-console-producer",
        "--bootstrap-server", "localhost:9092",
        "--topic", "weather.events",
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(input=line + "\n")
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to produce to Kafka: {stderr}")


def run_test():
    print("=" * 75)
    print("STARTING LIVE PGVECTOR DUPLICATE DETECTION TEST")
    print("=" * 75)

    # Step 1: Verify pgvector extension and column
    ext = psql_query_json("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
    print(f"[DB CHECK] pgvector extension installed: {ext}")
    assert len(ext) > 0, "pgvector extension not installed in postgres"

    col = psql_query_json("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'canonical_events' AND column_name = 'embedding'
    """)
    print(f"[DB CHECK] canonical_events.embedding column: {col}")
    assert len(col) > 0, "embedding column does not exist on canonical_events"

    # Step 2: Prepare Event 1
    event_1_id = str(uuid.uuid4())
    desc_1 = "Massive flash flooding along Ghodbunder Road causing traffic gridlock and stranded vehicles"
    now_ts = datetime.now(timezone.utc)
    test_city = f"Thane_{uuid.uuid4().hex[:6]}"

    event_1 = {
        "event_id": event_1_id,
        "source_type": "social",
        "source_name": "twitter_feed_alpha",
        "source_trust_score": 0.75,
        "timestamp": now_ts.isoformat(),
        "ingestion_timestamp": now_ts.isoformat(),
        "location": {
            "latitude": 19.2183,
            "longitude": 72.9781,
            "city": test_city,
            "district": "Thane",
            "state": "Maharashtra",
            "country": "India",
        },
        "event": {
            "category": "flood",
            "severity": "high",
            "description": desc_1,
        },
    }

    envelope_1 = {
        "schema_version": "1.0.0",
        "message_id": str(uuid.uuid4()),
        "event_type": "weather_event",
        "produced_at": now_ts.isoformat(),
        "producer": "integration_test",
        "payload": json.dumps(event_1),
    }

    print(f"\n[EVENT 1] Publishing Event 1 (ID: {event_1_id[:8]}...):")
    print(f"          City: '{test_city}'")
    print(f"          Description: '{desc_1}'")
    publish_kafka_envelope(envelope_1)

    # Poll DB for Event 1
    print("[EVENT 1] Waiting for Spark pg_writer to persist Event 1...")
    ce_1_id = None
    for _ in range(30):
        time.sleep(1)
        rows = psql_query_json(f"""
            SELECT e.event_id, e.canonical_event_id, e.duplicate_score,
                   (ce.embedding IS NOT NULL) AS has_embedding, ce.report_count
            FROM events e
            LEFT JOIN canonical_events ce ON e.canonical_event_id = ce.canonical_event_id
            WHERE e.event_id = '{event_1_id}'
        """)
        if rows and rows[0].get("canonical_event_id"):
            row = rows[0]
            ce_1_id = row["canonical_event_id"]
            print(f"[EVENT 1] Persisted! canonical_event_id={ce_1_id}, duplicate_score={row.get('duplicate_score')}, has_embedding={row.get('has_embedding')}")
            break

    assert ce_1_id is not None, "Event 1 was not persisted by pg_writer within 30s"

    # Step 3: Prepare Event 2 (Paraphrased with disjoint wording)
    event_2_id = str(uuid.uuid4())
    desc_2 = "Severe deluge submerging highway in Thane resulting in vehicular gridlock and submerged roadways"
    ts_2 = now_ts + timedelta(minutes=3)

    event_2 = {
        "event_id": event_2_id,
        "source_type": "citizen",
        "source_name": "citizen_report_beta",
        "source_trust_score": 0.70,
        "timestamp": ts_2.isoformat(),
        "ingestion_timestamp": ts_2.isoformat(),
        "location": {
            "latitude": 19.2185,
            "longitude": 72.9783,
            "city": test_city,
            "district": "Thane",
            "state": "Maharashtra",
            "country": "India",
        },
        "event": {
            "category": "flood",
            "severity": "high",
            "description": desc_2,
        },
    }

    envelope_2 = {
        "schema_version": "1.0.0",
        "message_id": str(uuid.uuid4()),
        "event_type": "weather_event",
        "produced_at": ts_2.isoformat(),
        "producer": "integration_test",
        "payload": json.dumps(event_2),
    }

    print(f"\n[EVENT 2] Publishing Paraphrased Event 2 (ID: {event_2_id[:8]}...):")
    print(f"          Description: '{desc_2}'")
    publish_kafka_envelope(envelope_2)

    # Poll DB for Event 2
    print("[EVENT 2] Waiting for Spark pg_writer to process Event 2...")
    event_2_row = None
    for _ in range(30):
        time.sleep(1)
        rows = psql_query_json(f"""
            SELECT e.event_id, e.canonical_event_id, e.duplicate_score,
                   e.verification_status, ce.report_count,
                   (ce.embedding IS NOT NULL) AS has_embedding
            FROM events e
            LEFT JOIN canonical_events ce ON e.canonical_event_id = ce.canonical_event_id
            WHERE e.event_id = '{event_2_id}'
        """)
        if rows and rows[0].get("duplicate_score") is not None:
            event_2_row = rows[0]
            break

    assert event_2_row is not None, "Event 2 was not persisted by pg_writer within 30s"
    ev2_id = event_2_row["event_id"]
    ce2_id = event_2_row["canonical_event_id"]
    dup_score_2 = float(event_2_row["duplicate_score"])
    ver_status_2 = event_2_row["verification_status"]
    rpt_cnt_2 = event_2_row["report_count"]

    print(f"\n[EVENT 2 PROCESSED RESULTS]:")
    print(f"  Event ID:            {ev2_id}")
    print(f"  Canonical Event ID:  {ce2_id}")
    print(f"  Duplicate Score:     {dup_score_2}")
    print(f"  Verification Status: {ver_status_2}")
    print(f"  Canonical Reports:   {rpt_cnt_2}")

    # Check pgvector cosine similarity directly via <=> query
    sim_rows = psql_query_json(f"""
        SELECT ce.canonical_event_id,
               1 - (ce.embedding <=> target.embedding) AS cosine_sim
        FROM canonical_events ce,
             (SELECT embedding FROM canonical_events WHERE canonical_event_id = '{ce_1_id}') target
        WHERE ce.canonical_event_id = '{ce2_id}' AND ce.embedding IS NOT NULL AND target.embedding IS NOT NULL
    """)
    cosine_sim = None
    if sim_rows:
        cosine_sim = float(sim_rows[0].get("cosine_sim"))
        print(f"  pgvector Cosine Sim: {cosine_sim:.4f}")

    # Check Jaccard word similarity between the two descriptions
    w1 = set(desc_1.lower().split())
    w2 = set(desc_2.lower().split())
    jaccard = len(w1 & w2) / len(w1 | w2)
    print(f"  Jaccard Word Sim:    {jaccard:.4f}")

    # Baseline without semantic similarity on the candidate canonical event:
    # Signals: text (0.30 * jaccard), category (0.15 * 1.0), distance (0.10 * 1.0), time (0.10 * 1.0)
    # Available weights: 0.30 + 0.15 + 0.10 + 0.10 = 0.65
    jaccard_only_score = round((0.30 * jaccard + 0.15 * 1.0 + 0.10 * 1.0 + 0.10 * 1.0) / 0.65, 3)
    expected_with_sem = round((0.30 * jaccard + 0.15 * 1.0 + 0.10 * 1.0 + 0.10 * 1.0 + 0.25 * (cosine_sim or 0.88)) / 0.90, 3)

    print(f"  Jaccard-Only Baseline (without semantic): {jaccard_only_score}")
    print(f"  Expected Score (with pgvector semantic):  {expected_with_sem}")
    print(f"  Actual Pipeline Score:                   {dup_score_2}")

    # Confirm semantic similarity score actually influenced the duplicate decision
    assert dup_score_2 > jaccard_only_score, f"Duplicate score ({dup_score_2}) was not influenced by semantic similarity (expected > {jaccard_only_score})"
    assert dup_score_2 >= 0.60, f"Duplicate score ({dup_score_2}) should cross possible_duplicate threshold (0.60)"
    assert jaccard_only_score < 0.60, f"Jaccard alone should be below possible_duplicate threshold (0.60), got {jaccard_only_score}"
    assert rpt_cnt_2 >= 2, f"Corroboration report count ({rpt_cnt_2}) did not increment"

    print("\n" + "=" * 75)
    print("TEST PASSED: pgvector semantic similarity successfully influenced duplicate pipeline!")
    print(f"  Jaccard-only score {jaccard_only_score} (< 0.60 not_duplicate) was boosted to {dup_score_2} (>= 0.60 possible_duplicate) by pgvector <=> similarity ({cosine_sim:.4f}).")
    print(f"  Corroboration report count incremented to {rpt_cnt_2}.")
    print("=" * 75)


if __name__ == "__main__":
    run_test()
