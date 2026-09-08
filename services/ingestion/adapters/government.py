"""Government dataset adapter for JSON, CSV and Parquet files."""
import csv, json, os
from datetime import datetime, timezone
from .common import make_event
class GovernmentAdapter:
    source_type="government_dataset"; source_name="government_dataset"
    def __init__(self): self.data_dir=os.environ.get("GOVERNMENT_DATA_DIR","/data/raw/government")
    def _records(self,path):
        if path.endswith(".json"):
            obj=json.load(open(path,encoding="utf-8")); return obj if isinstance(obj,list) else obj.get("records",[])
        if path.endswith(".csv"):
            with open(path,encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
        if path.endswith(".parquet"):
            try:
                import pandas as pd; return pd.read_parquet(path).to_dict("records")
            except Exception: return []
        return []
    def fetch_events(self):
        out=[]
        if not os.path.isdir(self.data_dir): return out
        for name in sorted(os.listdir(self.data_dir)):
            path=os.path.join(self.data_dir,name)
            for i,row in enumerate(self._records(path)):
                text=str(row.get("description") or row.get("text") or row.get("event_description") or "").strip()
                if not text: continue
                ts=str(row.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
                event = make_event("government_dataset", self.source_name, str(row.get("event_id") or f"{name}:{i}"), text, ts, row.get("source_url") or row.get("url"), row.get("category"), row.get("severity") or "moderate")
                try:
                    if row.get("latitude") is not None and row.get("longitude") is not None:
                        event["location"]["latitude"] = float(row["latitude"])
                        event["location"]["longitude"] = float(row["longitude"])
                    if row.get("city"): event["location"]["city"] = str(row["city"])
                    if row.get("district"): event["location"]["district"] = str(row["district"])
                    if row.get("state"): event["location"]["state"] = str(row["state"])
                except (TypeError, ValueError):
                    pass
                out.append(event)
        return out
