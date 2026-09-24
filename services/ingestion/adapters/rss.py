"""RSS feed adapter with GeoRSS coordinate extraction and hazard feed integration."""
import json
import logging
import os
import re
from datetime import datetime, timezone
import feedparser
from .common import make_event

logger = logging.getLogger("ingestion.rss")


def _extract_coords(entry):
    """Extract latitude and longitude from GeoRSS or feedparser location fields."""
    # 1. Direct feedparser geo_lat / geo_long
    lat = entry.get("geo_lat") or entry.get("latitude")
    lon = entry.get("geo_long") or entry.get("longitude")
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon)
        except (ValueError, TypeError):
            pass

    # 2. georss_point e.g. "16.5 -119.3" or "16.5, -119.3"
    pt = entry.get("georss_point") or entry.get("point")
    if pt and isinstance(pt, str):
        parts = re.split(r"[\s,]+", pt.strip())
        if len(parts) >= 2:
            try:
                return float(parts[0]), float(parts[1])
            except (ValueError, TypeError):
                pass

    # 3. GeoJSON-style where dict e.g. {'type': 'Point', 'coordinates': (-119.3, 16.5)}
    where = entry.get("where")
    if isinstance(where, dict) and "coordinates" in where:
        c = where["coordinates"]
        if len(c) >= 2:
            try:
                # GeoJSON coordinates order is (longitude, latitude)
                return float(c[1]), float(c[0])
            except (ValueError, TypeError):
                pass

    return None, None


class RssAdapter:
    source_type = "rss"
    source_name = "rss_feed"

    def __init__(self):
        cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "sources.json")
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            self.feeds = list(cfg.get("rss", {}).get("feeds", []))
        except Exception as exc:
            logger.warning("Failed to load sources.json: %s", exc)
            self.feeds = []

        # Integrate specific GDACS feeds from environment variables without duplication
        gdacs_env_feeds = [
            os.environ.get("GDACS_EARTHQUAKE_FEED_URL"),
            os.environ.get("GDACS_CYCLONE_FEED_URL"),
            os.environ.get("GDACS_FLOOD_FEED_URL"),
        ]
        for feed_url in gdacs_env_feeds:
            if feed_url and feed_url.strip() and feed_url.strip() not in self.feeds:
                self.feeds.append(feed_url.strip())

    def fetch_events(self):
        out = []
        seen_source_ids = set()

        for feed_url in self.feeds:
            try:
                parsed = feedparser.parse(feed_url)
            except Exception as exc:
                logger.warning("Failed to parse feed %s: %s", feed_url, exc)
                continue

            for i, entry in enumerate(parsed.entries[:50]):
                source_id = entry.get("id") or entry.get("guid") or f"{feed_url}#{i}"
                if source_id in seen_source_ids:
                    continue
                seen_source_ids.add(source_id)

                text = f"{entry.get('title', '')} {entry.get('summary', '')}".strip()
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

                lat, lon = _extract_coords(entry)

                # Derive category and severity if GDACS specific fields present
                cat = None
                sev = "moderate"
                event_type = (entry.get("gdacs_eventtype") or "").upper()
                if event_type == "TC":
                    cat = "cyclone"
                elif event_type == "FL":
                    cat = "flood"
                elif event_type == "EQ":
                    cat = "other"

                alert_level = (entry.get("gdacs_alertlevel") or "").lower()
                if alert_level == "red":
                    sev = "extreme"
                elif alert_level == "orange":
                    sev = "high"
                elif alert_level == "green":
                    sev = "moderate"

                country = entry.get("gdacs_country") or None

                out.append(
                    make_event(
                        source_type="rss",
                        source_name=self.source_name,
                        source_id=source_id,
                        text=text,
                        timestamp=ts,
                        url=entry.get("link"),
                        category=cat,
                        severity=sev,
                        latitude=lat,
                        longitude=lon,
                        country=country,
                    )
                )
        return out

