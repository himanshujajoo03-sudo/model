"""Controlled simulated social-media adapter."""
import json, os
from datetime import datetime, timezone
from .common import make_event
class SocialAdapter:
    source_type="simulated_social"; source_name="simulated_social_feed"
    def __init__(self):
        p=os.path.join(os.path.dirname(os.path.dirname(__file__)),"config","sources.json")
        self.feed_file=json.load(open(p,encoding="utf-8")).get("social",{}).get("feed_file")
    def fetch_events(self):
        records=[]
        if self.feed_file and os.path.exists(self.feed_file):
            with open(self.feed_file,encoding="utf-8") as f: records=json.load(f)
        else:
            records=[{"id":"social-demo-mumbai-001","text":"Heavy rain and waterlogging reported in Mumbai roads"}]
        now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return [make_event("simulated_social",self.source_name,str(x.get("id") or i),str(x.get("text") or x.get("description") or ""),x.get("timestamp") or now,x.get("url")) for i,x in enumerate(records) if str(x.get("text") or x.get("description") or "").strip()]
