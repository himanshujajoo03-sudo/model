"""
Open-Meteo Weather API Adapter.
Polls current weather observations for MVP cities (Mumbai, Nagpur, Nashik)
and converts responses into Canonical Weather Events.

Source of truth: 06_IMPLEMENTATION_PLAN.md §11, 02_DATA_SCHEMA.md §2.

Open-Meteo API: https://open-meteo.com/en/docs
- No API key required
- Returns WMO weather codes
- Returns current temperature, precipitation, wind speed, humidity
"""

import os
import json
import time
import logging
import uuid
import httpx
from datetime import datetime, timezone

from normaliser.canonical_event import (
    build_canonical_event,
    derive_event_category,
    SNOW_CODES,
)

logger = logging.getLogger("ingestion.openmeteo")

# ── Configuration from sources.json ─────────────────────────────────
# Loaded once at module level for fast access
_SOURCES_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "sources.json"
)

def _load_sources_config():
    """Load sources.json configuration."""
    try:
        with open(_SOURCES_CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load sources.json: %s", e)
        return {}


# ── Open-Meteo City Definitions ─────────────────────────────────────
# From 06_IMPLEMENTATION_PLAN.md §11 and sources.json
CITIES = [
    {
        "name": "Mumbai",
        "district": "Mumbai City",
        "state": "Maharashtra",
        "latitude": 19.076,
        "longitude": 72.878,
    },
    {
        "name": "Nagpur",
        "district": "Nagpur",
        "state": "Maharashtra",
        "latitude": 21.146,
        "longitude": 79.088,
    },
    {
        "name": "Nashik",
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": 19.997,
        "longitude": 73.790,
    },
]

# ── Open-Meteo API ──────────────────────────────────────────────────
BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Current weather variables needed for the canonical event
CURRENT_WEATHER_PARAMS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
]


class OpenMeteoAdapter:
    """
    Polls Open-Meteo for current weather observations and produces
    Canonical Weather Events to Kafka weather.raw.

    Usage:
        adapter = OpenMeteoAdapter(produce_fn=my_produce_fn)
        adapter.run_once()  # Single poll cycle
        # or
        adapter.run_loop()  # Continuous polling
    """

    def __init__(self, produce_fn, poll_interval_seconds=300):
        self.produce_fn = produce_fn
        self.poll_interval = int(
            os.environ.get("OPENMETEO_POLL_INTERVAL_SECONDS", poll_interval_seconds)
        )
        self.timeout = 10  # seconds
        self._client = httpx.Client(timeout=self.timeout)
        logger.info(
            "Open-Meteo adapter initialized — poll_interval=%ds, cities=%s",
            self.poll_interval,
            [c["name"] for c in CITIES],
        )

    def run_once(self):
        """Execute a single polling cycle: fetch all cities, normalize, publish."""
        logger.info("Open-Meteo poll cycle starting — %d cities", len(CITIES))
        published = 0
        for city in CITIES:
            try:
                event = self._process_city(city)
                if event is not None:
                    published += 1
            except Exception as e:
                logger.warning(
                    "Failed to process city %s: %s", city["name"], e, exc_info=True
                )
        logger.info("Open-Meteo poll cycle complete — %d/%d events published",
                     published, len(CITIES))
        return published

    def run_loop(self):
        """Continuous polling loop. Runs forever with configured interval."""
        logger.info(
            "Open-Meteo polling loop starting — interval=%ds", self.poll_interval
        )
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error("Open-Meteo poll cycle failed: %s", e, exc_info=True)
            logger.info(
                "Open-Meteo sleeping %ds until next poll cycle", self.poll_interval
            )
            time.sleep(self.poll_interval)

    def _process_city(self, city):
        """Fetch weather for one city, normalize, and publish to Kafka."""
        logger.info("Fetching weather for %s (%.3f, %.3f)",
                     city["name"], city["latitude"], city["longitude"])

        weather_data = self._fetch_weather(city["latitude"], city["longitude"])
        if weather_data is None:
            return None

        canonical = self._normalize(city, weather_data)
        if canonical is None:
            return None

        self.produce_fn(canonical)
        logger.info(
            "Published %s event: city=%s category=%s severity=%s temp=%.1f°C",
            city["name"],
            canonical["location"]["city"],
            canonical["event"]["category"],
            canonical["event"]["severity"],
            weather_data.get("temperature_2m", 0),
        )
        return canonical

    def _fetch_weather(self, latitude, longitude):
        """
        Fetch current weather from Open-Meteo.

        Endpoint: GET https://api.open-meteo.com/v1/forecast
        Returns: dict with 'current' key containing weather observations.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(CURRENT_WEATHER_PARAMS),
            "timezone": "Asia/Kolkata",
        }

        try:
            resp = self._client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current")
            if current is None:
                logger.warning("Open-Meteo returned no 'current' data for %.3f,%.3f",
                               latitude, longitude)
                return None

            return current

        except httpx.TimeoutException:
            logger.warning("Open-Meteo request timed out for %.3f,%.3f", latitude, longitude)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("Open-Meteo HTTP error %s for %.3f,%.3f",
                           e.response.status_code, latitude, longitude)
            return None
        except Exception as e:
            logger.warning("Open-Meteo request failed for %.3f,%.3f: %s",
                           latitude, longitude, e)
            return None

    def _normalize(self, city, current):
        """
        Normalize Open-Meteo current weather data into a Canonical Weather Event.

        Returns: dict matching 02_DATA_SCHEMA.md §2, or None if no event-worthy
        weather condition detected.
        """
        weather_code = current.get("weather_code")
        temperature_c = current.get("temperature_2m")
        precipitation_mm = current.get("precipitation", 0.0)
        wind_speed_kmh = current.get("wind_speed_10m")
        humidity_pct = current.get("relative_humidity_2m")
        wind_dir = current.get("wind_direction_10m")

        # Map WMO code + measurements to event category
        category, severity = derive_event_category(
            weather_code,
            temperature_c=temperature_c,
            wind_speed_kmh=wind_speed_kmh,
            precipitation_mm=precipitation_mm,
        )

        if category is None:
            # Enhanced snow logging with city/location/timestamp context
            if weather_code in SNOW_CODES:
                time_str = current.get("time", "unknown")
                logger.info(
                    "Unsupported snow weather code %d for %s (%.3f, %.3f) at %s; skipping observation",
                    weather_code, city["name"], city["latitude"], city["longitude"], time_str,
                )
            else:
                logger.debug(
                    "Skipping benign weather for %s: code=%s temp=%s precip=%s wind=%s",
                    city["name"], weather_code, temperature_c, precipitation_mm, wind_speed_kmh,
                )
            return None

        # Build description from actual measurements
        description = self._build_description(
            city["name"], category, weather_code,
            temperature_c, precipitation_mm, wind_speed_kmh, humidity_pct, wind_dir
        )

        # Parse Open-Meteo timestamp to ISO 8601 UTC
        time_str = current.get("time", "")
        event_timestamp = self._parse_timestamp(time_str)

        # Source metadata
        source_id = "openmeteo_{city}_{ts}".format(
            city=city["name"].lower(),
            ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ"),
        )

        return build_canonical_event(
            source_type="weather_api",
            source_name="Open-Meteo",
            source_id=source_id,
            description=description,
            category=category,
            location={
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "city": city["name"],
                "district": city["district"],
                "state": city["state"],
                "country": "India",
            },
            timestamp=event_timestamp,
            source_url="https://api.open-meteo.com/v1/forecast",
            severity=severity,
            hashtags=["#OpenMeteo", f"#{city['name']}Weather"],
        )

    def _build_description(self, city_name, category, weather_code,
                           temperature_c, precipitation_mm, wind_speed_kmh,
                           humidity_pct, wind_dir):
        """Build a human-readable description from measurements."""
        parts = []

        if category == "heatwave":
            parts.append(f"Heatwave conditions in {city_name} with temperature at {temperature_c}°C")
        elif category == "heavy_rainfall":
            if precipitation_mm and precipitation_mm > 0:
                parts.append(f"Heavy rainfall recorded in {city_name} with {precipitation_mm:.1f}mm precipitation")
            else:
                parts.append(f"Heavy rainfall conditions in {city_name}")
        elif category == "thunderstorm":
            parts.append(f"Thunderstorm activity in {city_name}")
            if precipitation_mm and precipitation_mm > 0:
                parts.append(f"with {precipitation_mm:.1f}mm precipitation")
        elif category == "fog":
            parts.append(f"Foggy conditions in {city_name}")
        elif category == "strong_wind":
            if wind_speed_kmh:
                parts.append(f"Strong winds in {city_name} at {wind_speed_kmh:.0f} km/h")
            else:
                parts.append(f"Strong wind conditions in {city_name}")
        else:
            parts.append(f"Weather event in {city_name}")

        # Add temperature context
        if temperature_c is not None:
            parts.append(f"Temperature: {temperature_c}°C")

        # Add wind info for non-wind categories
        if category != "strong_wind" and wind_speed_kmh is not None:
            parts.append(f"Wind: {wind_speed_kmh:.0f} km/h")

        return ". ".join(parts) + "."

    def _parse_timestamp(self, time_str):
        """
        Parse Open-Meteo time string to ISO 8601 UTC.

        Open-Meteo returns times like "2026-09-02T14:30" (Asia/Kolkata timezone).
        We convert to UTC.
        """
        if not time_str:
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        try:
            # Open-Meteo with timezone=Asia/Kolkata returns local time strings
            # Parse as naive (IST = UTC+5:30) and convert
            from datetime import timedelta

            # If it ends with 'Z', it's already UTC
            if time_str.endswith("Z"):
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            elif "+" in time_str or time_str.count("-") > 2:
                # Has timezone offset
                dt = datetime.fromisoformat(time_str)
            else:
                # Naive local time in IST (UTC+5:30)
                dt_naive = datetime.fromisoformat(time_str)
                # IST is UTC+5:30
                ist_offset = timedelta(hours=5, minutes=30)
                dt = dt_naive.replace(tzinfo=timezone.utc) - ist_offset

            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        except Exception as e:
            logger.warning("Failed to parse timestamp '%s': %s — using current time", time_str, e)
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def close(self):
        """Close the HTTP client."""
        self._client.close()
