"""Deterministic architecture/contract gate for SIH26069."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
def text(p): return (ROOT/p).read_text(encoding='utf-8')

main=text('services/api/main.py'); citizen=text('services/api/routers/citizen.py')
verification=text('services/api/routers/verification.py'); kafka=text('services/api/services/kafka_service.py')
stream=text('services/spark/jobs/stream_processor.py'); pg=text('services/spark/jobs/pg_writer.py')
compose=text('docker-compose.yml'); client=text('services/frontend/src/api/client.js'); app=text('services/frontend/src/App.jsx')
checks={
 'citizen router registered': 'app.include_router(citizen_router, prefix="/api/v1")' in main,
 'citizen variables defined': all(x in citizen for x in ('photo_urls = await', 'video_urls = await', 'event_timestamp = _parse_timestamp')),
 'citizen adapter path': 'normalize_citizen_report(' in citizen and 'citizen.raw' in kafka,
 'admin login route': '/auth/login' in text('services/api/routers/auth.py') and 'path="/login"' in app,
 'frontend JWT attachment': 'headers.set(\'Authorization\', `Bearer ${token}`)' in client,
 'verification transactional outbox': 'enqueue(conn' in verification and 'verification_outbox' in text('services/api/services/verification_outbox.py') and '"weather.verified"' in text('services/api/services/verification_outbox.py'),
 'weather.events envelope': '"value": json.dumps(envelope)' in stream and 'required = ("schema_version"' in pg,
 'postgres migration service': 'db-migrate:' in compose and '02_canonical_events.sql' in compose,
 'kafka init service': 'kafka-init:' in compose and 'weather.verified' in compose,
 'historical parquet writer': 'partitionBy("year", "month", "day").parquet("/data/processed/weather_events")' in stream,
 'sklearn aligned': 'scikit-learn==1.7.2' in text('services/ml/requirements.txt') and 'MODEL_PATH=/opt/models/event_classifier/model.pkl' in text('.env'),
 'spark dedup watermark': 'withWatermark("event_time", "30 minutes")' in stream and 'dropDuplicates(["event_id"])' in stream,
 'spark aggregation exposed': 'ai_payload["aggregation_count"]' in stream,
 'durable cluster state': '_load_cluster_state()' in stream and '_save_cluster_state(proposed_cluster_state)' in stream and '_save_cluster_state(active)' not in stream,
 'frontend citizen page': 'path="/citizen-report"' in app and (ROOT/'services/frontend/src/pages/CitizenReport.jsx').exists(),
}
failed=[k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('PASS' if v else 'FAIL'), k)
if failed:
    raise SystemExit('Architecture gate failed: '+', '.join(failed))
print(f'Architecture gate passed: {len(checks)}/{len(checks)}')
