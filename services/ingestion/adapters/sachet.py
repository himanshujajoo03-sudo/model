"""
Sachet / NDMA Common Alerting Protocol (CAP) RSS Feed Adapter.
National Disaster Management Authority (India) live disaster alerts.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
import feedparser
from .common import make_event, infer_category, infer_city

logger = logging.getLogger("ingestion.sachet")

DEFAULT_SACHET_FEED_URL = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"


def _extract_state_from_author(author: str | None) -> str | None:
    """Extract Indian State or SDMA name from author tag (e.g. 'controlroom@ndma.gov.in (Andhra Pradesh SDMA)')."""
    if not author:
        return None
    match = re.search(r"\(([^)]+)\)", author)
    if match:
        raw = match.group(1).replace("SDMA", "").replace("IMD", "").strip()
        if raw:
            return raw
    return None


def _derive_severity(title: str) -> str:
    """Infer alert severity from title contents."""
    t = title.lower()
    if any(w in t for w in ("extreme", "red alert", "severe", "very severe", "danger")):
        return "extreme"
    if any(w in t for w in ("warning", "orange alert", "heavy", "moderate", "intense")):
        return "high"
    return "moderate"


class SachetAdapter:
    source_type = "rss"
    source_name = "sachet_ndma"


    def __init__(self):
        self.feed_url = os.environ.get("SACHET_FEED_URL", DEFAULT_SACHET_FEED_URL).strip()

    def fetch_events(self, limit: int = 50):
        """Fetch and parse live disaster alerts from Sachet NDMA."""
        out = []
        if not self.feed_url:
            logger.warning("SACHET_FEED_URL is empty; skipping Sachet ingestion")
            return out

        try:
            parsed = feedparser.parse(self.feed_url)
        except Exception as exc:
            logger.warning("Failed to parse Sachet NDMA feed %s: %s", self.feed_url, exc)
            return out

        if parsed.bozo and not parsed.entries:
            logger.warning("Sachet feed returned parsing exception: %s", getattr(parsed, "bozo_exception", None))
            return out

        seen_ids = set()
        for i, entry in enumerate(parsed.entries[:limit]):
            alert_id = entry.get("id") or entry.get("guid") or f"sachet_entry_{i}"
            if alert_id in seen_ids:
                continue
            seen_ids.add(alert_id)

            title = (entry.get("title") or "").strip()
            summary = (entry.get("summary") or "").strip()
            text = f"{title} {summary}".strip()
            if not text:
                continue

            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if entry.get("published_parsed"):
                try:
                    ts = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"
                    )
                except Exception:
                    pass

            state = _extract_state_from_author(entry.get("author"))
            severity = _derive_severity(title)
            category = infer_category(text)
            if category == "other" and any(w in text.lower() for w in ("lightning", "thunderstorm", "పిడుగులు")):
                category = "lightning"

            # Check if text references a known city
            city = infer_city(text)

            event = make_event(
                source_type=self.source_type,
                source_name=self.source_name,
                source_id=f"sachet_{alert_id}",
                text=text,
                timestamp=ts,
                url=entry.get("link"),
                category=category,
                severity=severity,
                city=city,
                state=state,
                country="India",
            )
            out.append(event)

        return out
