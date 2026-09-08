from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG = (ROOT / 'services/spark/jobs/pg_writer.py').read_text()
SPARK = (ROOT / 'services/spark/jobs/stream_processor.py').read_text()


def test_report_count_is_conditional_on_new_source_event():
    assert 'report_count = report_count + CASE WHEN %s THEN 1 ELSE 0 END' in PG
    assert 'increment_report_count=not source_event_exists' in PG


def test_canonical_time_and_severity_are_event_time_safe():
    assert 'first_seen = LEAST(first_seen, %s)' in PG
    assert "WHEN 'extreme' THEN 3" in PG


def test_cluster_membership_is_idempotent():
    assert 'event_cluster_members' in PG
    assert 'ON CONFLICT (event_id) DO NOTHING' in PG


def test_cluster_state_commit_happens_after_parquet_success():
    assert 'proposed_cluster_state' in SPARK
    parquet_pos = SPARK.index('parquet_df.write.mode("append")')
    state_pos = SPARK.index('_save_cluster_state(proposed_cluster_state)')
    assert parquet_pos < state_pos
    assert '_save_cluster_state(active)' not in SPARK
