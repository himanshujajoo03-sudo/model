"""Allow-listed website adapter with graceful access-control and error handling."""
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
from .common import make_event, infer_city

logger = logging.getLogger("ingestion.website")

# Cooldown period (in seconds) before re-attempting a blocked/restricted site
BLOCKED_COOLDOWN_SECONDS = 3600  # 1 hour


class WebsiteAdapter:
    source_type = "website"
    source_name = "allowlisted_weather_web"

    def __init__(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "website_allowlist.json")
        try:
            with open(config_path, encoding="utf-8") as f:
                self.urls = json.load(f).get("allowed_urls", [])
        except Exception as exc:
            logger.warning("Failed to load website allowlist: %s", exc)
            self.urls = []
        # Track last failure time for blocked URLs to prevent repeated noisy requests
        self._blocked_cooldowns: dict[str, float] = {}

    def fetch_events(self):
        out = []
        now = time.time()

        for url in self.urls:
            # Check if URL is in cooldown
            last_blocked = self._blocked_cooldowns.get(url, 0)
            if now - last_blocked < BLOCKED_COOLDOWN_SECONDS:
                continue

            try:
                headers = {"User-Agent": "SIH26069-weather-platform/1.0 (Disaster Resilience Analytics)"}
                r = httpx.get(url, timeout=10, follow_redirects=True, headers=headers)
                r.raise_for_status()

                text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
                if not re.search(r"rain|storm|flood|heat|wind|fog|hail|cyclone|lightning", text, re.I):
                    continue

                city = infer_city(text)
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                out.append(
                    make_event(
                        source_type=self.source_type,
                        source_name=self.source_name,
                        source_id=url,
                        text=text[:2000],
                        timestamp=ts,
                        url=url,
                        city=city,
                    )
                )
            except httpx.HTTPStatusError as err:
                status_code = err.response.status_code
                if status_code in (403, 401, 429):
                    logger.warning(
                        "Website %s is restricted/protected by upstream (HTTP %d). Entering cooldown for %ds.",
                        url,
                        status_code,
                        BLOCKED_COOLDOWN_SECONDS,
                    )
                    self._blocked_cooldowns[url] = now
                else:
                    logger.warning("HTTP error while fetching %s: %s", url, err)
            except httpx.RequestError as err:
                logger.warning("Network connection failed for %s: %s", url, err)
            except Exception as exc:
                logger.warning("Unexpected error scraping %s: %s", url, exc)

        return out

