"""Real PostgreSQL/PostGIS integration tests for the persistence invariants.

Run with TEST_DATABASE_URL pointing at a disposable PostGIS database. The suite
creates isolated rows and cleans them up after each test.
"""
import os, uuid
from datetime import datetime, timezone, timedelta
import pytest

psycopg2 = pytest.importorskip("psycopg2")
DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not configured")

from services.spark.jobs.pg_writer import _upsert_canonical_event, _upsert_event, _persist_cluster_assignment

@pytest.fixture
def db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


def event(event_id=None, source_type="citizen", ts=None, severity="low", cluster_id=None):
    return {
        "event_id": str(event_id or uuid.uuid4()), "source_id": "test-source", "source_type": source_type,
        "source_name": source_type, "timestamp": (ts or datetime.now(timezone.utc)).isoformat(),
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "location": {"latitude": 18.52, "longitude": 73.85, "city": "Pune", "state": "Maharashtra", "country": "India"},
        "event": {"category": "heavy_rainfall", "severity": severity, "description": "integration"},
        "ai": {"classification_confidence": .8, "credibility_score": .7, "cluster_id": cluster_id},
        "verification": {"status": "pending", "verification_reasons": []},
        "social_metadata": {}, "media": {},
    }


def insert_source_and_canonical(conn, ev, ce_id=None, increment=True):
    cid = _upsert_canonical_event(conn, ev, ce_id, increment_report_count=increment)
    ok, inserted = _upsert_event(conn, ev)
    assert ok
    return cid, inserted


def test_new_canonical_event(db):
    cid, inserted = insert_source_and_canonical(db, event())
    assert inserted
    with db.cursor() as c:
        c.execute("SELECT report_count, source_count FROM canonical_events WHERE canonical_event_id=%s", (cid,))
        assert c.fetchone() == (1, 1)


def test_second_report_increments_report_count(db):
    e1, e2 = event(), event(source_type="social")
    cid, _ = insert_source_and_canonical(db, e1)
    cid2, inserted = insert_source_and_canonical(db, e2, cid, True)
    assert cid == cid2 and inserted
    with db.cursor() as c:
        c.execute("SELECT report_count, source_count FROM canonical_events WHERE canonical_event_id=%s", (cid,))
        assert c.fetchone() == (2, 2)


def test_same_source_does_not_increment_source_count(db):
    e1, e2 = event(), event()
    cid, _ = insert_source_and_canonical(db, e1)
    insert_source_and_canonical(db, e2, cid, True)
    with db.cursor() as c:
        c.execute("SELECT report_count, source_count FROM canonical_events WHERE canonical_event_id=%s", (cid,))
        assert c.fetchone() == (2, 1)


def test_different_source_increments_source_count(db):
    e1, e2 = event(source_type="citizen"), event(source_type="rss")
    cid, _ = insert_source_and_canonical(db, e1)
    insert_source_and_canonical(db, e2, cid, True)
    with db.cursor() as c:
        c.execute("SELECT source_count FROM canonical_events WHERE canonical_event_id=%s", (cid,))
        assert c.fetchone()[0] == 2

@pytest.mark.parametrize("old,new,expected", [("low","extreme","extreme"),("extreme","low","extreme")])
def test_severity_low_to_extreme(db, old, new, expected):
    cid,_=insert_source_and_canonical(db,event(severity=old))
    insert_source_and_canonical(db,event(severity=new),cid,True)
    with db.cursor() as c:
        c.execute("SELECT severity FROM canonical_events WHERE canonical_event_id=%s",(cid,))
        assert c.fetchone()[0]==expected

def test_first_seen_late_arrival(db):
    late=datetime(2026,9,8,12,tzinfo=timezone.utc); early=late-timedelta(hours=2)
    cid,_=insert_source_and_canonical(db,event(ts=late))
    insert_source_and_canonical(db,event(source_type="rss",ts=early),cid,True)
    with db.cursor() as c:
        c.execute("SELECT first_seen,last_seen FROM canonical_events WHERE canonical_event_id=%s",(cid,))
        first,last=c.fetchone(); assert first==early and last==late

def test_last_seen(db):
    t1=datetime(2026,9,8,10,tzinfo=timezone.utc); t2=t1+timedelta(hours=3)
    cid,_=insert_source_and_canonical(db,event(ts=t1))
    insert_source_and_canonical(db,event(source_type="rss",ts=t2),cid,True)
    with db.cursor() as c:
        c.execute("SELECT last_seen FROM canonical_events WHERE canonical_event_id=%s",(cid,))
        assert c.fetchone()[0]==t2

def test_cluster_id_persistence(db):
    cluster=str(uuid.uuid4()); ev=event(cluster_id=cluster)
    cid,_=insert_source_and_canonical(db,ev)
    with db.cursor() as c:
        c.execute("SELECT cluster_id FROM canonical_events WHERE canonical_event_id=%s",(cid,))
        assert str(c.fetchone()[0])==cluster

def test_cluster_member_count(db):
    cluster=str(uuid.uuid4()); ev=event(cluster_id=cluster)
    _persist_cluster_assignment(db,ev); _upsert_event(db,ev)
    with db.cursor() as c:
        c.execute("SELECT member_count FROM event_clusters WHERE cluster_id=%s",(cluster,))
        assert c.fetchone()[0]==1

def test_cluster_replay(db):
    cluster=str(uuid.uuid4()); ev=event(cluster_id=cluster)
    _persist_cluster_assignment(db,ev); _upsert_event(db,ev)
    _persist_cluster_assignment(db,ev)
    with db.cursor() as c:
        c.execute("SELECT member_count FROM event_clusters WHERE cluster_id=%s",(cluster,))
        assert c.fetchone()[0]==1

def test_postgres_failure_rolls_back(db):
    ev=event(); cid,_=insert_source_and_canonical(db,ev)
    with pytest.raises(Exception):
        with db.cursor() as c:
            c.execute("INSERT INTO events(event_id,source_id,source_type,event_timestamp) VALUES (%s,%s,%s,%s)",
                      (str(uuid.uuid4()),"x","not_a_real_source",datetime.now(timezone.utc)))
    db.rollback()
    with db.cursor() as c:
        c.execute("SELECT report_count FROM canonical_events WHERE canonical_event_id=%s",(cid,))
        assert c.fetchone() is None
