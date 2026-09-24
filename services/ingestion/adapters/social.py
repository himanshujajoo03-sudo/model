"""
Social media adapter supporting live Mastodon API and simulated feed fallback.
Ref: 01_ARCHITECTURE.md §4.1, 02_DATA_SCHEMA.md §2
"""
import json
import logging
import os
import re
from datetime import datetime, timezone
import httpx
from .common import make_event

logger = logging.getLogger("ingestion.social")


class SocialAdapter:
    source_type = "social"
    source_name = "mastodon"

    def __init__(self):
        self.base_url = os.environ.get("MASTODON_BASE_URL", "").rstrip("/")
        self.access_token = os.environ.get("MASTODON_ACCESS_TOKEN", "").strip()
        self.tag = os.environ.get("MASTODON_TAG", "weather").strip()
        self.limit = int(os.environ.get("MASTODON_LIMIT", "20"))
        p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "sources.json")
        self.feed_file = None
        if os.path.exists(p):
            try:
                self.feed_file = json.load(open(p, encoding="utf-8")).get("social", {}).get("feed_file")
            except Exception:
                pass

    def fetch_events(self):
        # 1. Attempt live Mastodon API if configured
        if self.base_url:
            try:
                events = self._fetch_mastodon()
                if events:
                    return events
            except Exception as exc:
                logger.warning("Mastodon API fetch failed, falling back to simulated feed: %s", exc)

        # 2. Fallback to simulated feed file / default demo record
        return self._fetch_simulated()

    def _fetch_mastodon(self):
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        url = f"{self.base_url}/api/v1/timelines/tag/{self.tag}"
        resp = httpx.get(url, headers=headers, params={"limit": self.limit}, timeout=10)
        if resp.status_code != 200:
            logger.warning("Mastodon API returned status %d", resp.status_code)
            return []
        posts = resp.json()
        if not isinstance(posts, list):
            return []

        out = []
        for post in posts:
            raw_html = post.get("content") or ""
            clean_text = re.sub(r"<[^>]+>", " ", raw_html).strip()
            clean_text = " ".join(clean_text.split())
            if not clean_text:
                continue
            post_id = str(post.get("id") or "")
            created_at = post.get("created_at")
            url = post.get("url")
            event = make_event(
                source_type="social",
                source_name="mastodon",
                source_id=f"mastodon:{post_id}",
                text=clean_text,
                timestamp=created_at,
                url=url,
            )
            out.append(event)
        return out

    def _fetch_simulated(self):
        records = []
        if self.feed_file and os.path.exists(self.feed_file):
            with open(self.feed_file, encoding="utf-8") as f:
                records = json.load(f)
        else:
            records = [{"id": "social-demo-mumbai-001", "text": "Heavy rain and waterlogging reported in Mumbai roads"}]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return [
            make_event(
                "simulated_social",
                "simulated_social_feed",
                str(x.get("id") or i),
                str(x.get("text") or x.get("description") or ""),
                x.get("timestamp") or now,
                x.get("url"),
                latitude=x.get("latitude"),
                longitude=x.get("longitude"),
                city=x.get("city"),
            )
            for i, x in enumerate(records)
            if str(x.get("text") or x.get("description") or "").strip()
        ]

