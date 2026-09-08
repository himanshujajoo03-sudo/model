"""RSS feed adapter."""
import json, os
from datetime import datetime, timezone
import feedparser
from .common import make_event
class RssAdapter:
    source_type="rss"; source_name="rss_feed"
    def __init__(self):
        cfg_path=os.path.join(os.path.dirname(os.path.dirname(__file__)),"config","sources.json")
        cfg=json.load(open(cfg_path,encoding="utf-8")); self.feeds=cfg.get("rss",{}).get("feeds",[])
    def fetch_events(self):
        out=[]
        for feed_url in self.feeds:
            parsed=feedparser.parse(feed_url)
            for i,entry in enumerate(parsed.entries[:50]):
                text=f"{entry.get('title','')} {entry.get('summary','')}".strip()
                if not text: continue
                ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                if entry.get("published_parsed"):
                    ts=datetime(*entry.published_parsed[:6],tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                out.append(make_event("rss",self.source_name,entry.get("id") or f"{feed_url}#{i}",text,ts,entry.get("link")))
        return out
