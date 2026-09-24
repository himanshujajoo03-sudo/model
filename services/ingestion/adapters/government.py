"""Government dataset adapter for local filesystem (/data/raw/government) and registered data.gov.in resource endpoints."""
import csv
import json
import logging
import os
from datetime import datetime, timezone
import httpx
from .common import make_event

logger = logging.getLogger("ingestion.government")


class GovernmentAdapter:
    source_type = "government_dataset"
    source_name = "government_dataset"

    def __init__(self):
        configured_dir = os.environ.get("GOVERNMENT_DATA_DIR", "/data/raw/government")
        if not os.path.isdir(configured_dir):
            repo_local = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "raw", "government")
            if os.path.isdir(repo_local):
                configured_dir = repo_local
        self.data_dir = configured_dir
        self.api_key = os.environ.get("DATA_GOV_API_KEY", "").strip()
        # Optional registered data.gov.in resource URL (e.g. https://api.data.gov.in/resource/<resource_id>)
        self.resource_url = os.environ.get("DATA_GOV_RESOURCE_URL", "").strip()

    def _records(self, path):
        if path.endswith(".json"):
            try:
                obj = json.load(open(path, encoding="utf-8"))
                return obj if isinstance(obj, list) else obj.get("records", [])
            except Exception as exc:
                logger.warning("Failed to parse JSON file %s: %s", path, exc)
                return []
        if path.endswith(".csv"):
            try:
                with open(path, encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f))
            except Exception as exc:
                logger.warning("Failed to parse CSV file %s: %s", path, exc)
                return []
        if path.endswith(".parquet"):
            try:
                import pandas as pd
                return pd.read_parquet(path).to_dict("records")
            except Exception:
                return []
        return []

    def fetch_events(self):
        out = []

        # 1. Fetch from live data.gov.in resource endpoint if configured
        if self.resource_url and self.api_key:
            try:
                params = {"api-key": self.api_key, "format": "json", "limit": "50"}
                resp = httpx.get(self.resource_url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("records", []) if isinstance(data, dict) else []
                    for i, row in enumerate(records):
                        text = str(row.get("description") or row.get("text") or row.get("event_description") or "").strip()
                        if not text:
                            continue
                        ts = str(row.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
                        out.append(
                            make_event(
                                source_type=self.source_type,
                                source_name=self.source_name,
                                source_id=str(row.get("event_id") or f"datagov:{i}"),
                                text=text,
                                timestamp=ts,
                                url=self.resource_url,
                                category=row.get("category"),
                                severity=row.get("severity") or "moderate",
                                latitude=row.get("latitude"),
                                longitude=row.get("longitude"),
                                city=row.get("city"),
                                district=row.get("district"),
                                state=row.get("state"),
                            )
                        )
                else:
                    logger.warning("data.gov.in resource endpoint returned status %d", resp.status_code)
            except Exception as exc:
                logger.warning("Failed to fetch from data.gov.in resource: %s", exc)

        # 2. Ingest from local filesystem directory (/data/raw/government)
        if os.path.isdir(self.data_dir):
            for name in sorted(os.listdir(self.data_dir)):
                path = os.path.join(self.data_dir, name)
                for i, row in enumerate(self._records(path)):
                    text = str(row.get("description") or row.get("text") or row.get("event_description") or "").strip()
                    if not text:
                        continue
                    ts = str(row.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
                    event = make_event(
                        source_type=self.source_type,
                        source_name=self.source_name,
                        source_id=str(row.get("event_id") or f"{name}:{i}"),
                        text=text,
                        timestamp=ts,
                        url=row.get("source_url") or row.get("url"),
                        category=row.get("category"),
                        severity=row.get("severity") or "moderate",
                        latitude=row.get("latitude"),
                        longitude=row.get("longitude"),
                        city=row.get("city"),
                        district=row.get("district"),
                        state=row.get("state"),
                    )
                    out.append(event)

        return out

