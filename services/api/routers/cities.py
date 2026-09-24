"""
Cities router — GET /cities
Lists all registered Indian cities and their meteorological monitoring coverage.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from dependencies import get_db

router = APIRouter(tags=["cities"])

CANDIDATE_PATHS = [
    Path(__file__).resolve().parent.parent.parent / "ingestion" / "config" / "sources.json",
    Path("/app/config/sources.json"),
    Path(__file__).resolve().parent.parent / "config" / "sources.json",
    Path("services/ingestion/config/sources.json"),
]

ALL_DEFAULT_CITIES = [
    {"name": "Mumbai", "district": "Mumbai City", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    {"name": "Nagpur", "district": "Nagpur", "state": "Maharashtra", "latitude": 21.1458, "longitude": 79.0882},
    {"name": "Nashik", "district": "Nashik", "state": "Maharashtra", "latitude": 19.9975, "longitude": 73.7898},
    {"name": "Pune", "district": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
    {"name": "Delhi", "district": "New Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"name": "Agra", "district": "Agra", "state": "Uttar Pradesh", "latitude": 27.1767, "longitude": 78.0081},
    {"name": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"name": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    {"name": "Kolkata", "district": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639},
    {"name": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    {"name": "Ahmedabad", "district": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    {"name": "Surat", "district": "Surat", "state": "Gujarat", "latitude": 21.1702, "longitude": 72.8311},
    {"name": "Jaipur", "district": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    {"name": "Lucknow", "district": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    {"name": "Varanasi", "district": "Varanasi", "state": "Uttar Pradesh", "latitude": 25.3176, "longitude": 82.9739},
    {"name": "Kanpur", "district": "Kanpur Nagar", "state": "Uttar Pradesh", "latitude": 26.4499, "longitude": 80.3319},
    {"name": "Chandigarh", "district": "Chandigarh", "state": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794},
    {"name": "Amritsar", "district": "Amritsar", "state": "Punjab", "latitude": 31.6340, "longitude": 74.8723},
    {"name": "Shimla", "district": "Shimla", "state": "Himachal Pradesh", "latitude": 31.1048, "longitude": 77.1734},
    {"name": "Dehradun", "district": "Dehradun", "state": "Uttarakhand", "latitude": 30.3165, "longitude": 78.0322},
    {"name": "Srinagar", "district": "Srinagar", "state": "Jammu and Kashmir", "latitude": 34.0837, "longitude": 74.7973},
    {"name": "Bhopal", "district": "Bhopal", "state": "Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126},
    {"name": "Indore", "district": "Indore", "state": "Madhya Pradesh", "latitude": 22.7196, "longitude": 75.8577},
    {"name": "Patna", "district": "Patna", "state": "Bihar", "latitude": 25.5941, "longitude": 85.1376},
    {"name": "Ranchi", "district": "Ranchi", "state": "Jharkhand", "latitude": 23.3441, "longitude": 85.3096},
    {"name": "Bhubaneswar", "district": "Khordha", "state": "Odisha", "latitude": 20.2961, "longitude": 85.8245},
    {"name": "Puri", "district": "Puri", "state": "Odisha", "latitude": 19.8135, "longitude": 85.8312},
    {"name": "Raipur", "district": "Raipur", "state": "Chhattisgarh", "latitude": 21.2514, "longitude": 81.6296},
    {"name": "Kochi", "district": "Ernakulam", "state": "Kerala", "latitude": 9.9312, "longitude": 76.2673},
    {"name": "Thiruvananthapuram", "district": "Thiruvananthapuram", "state": "Kerala", "latitude": 8.5241, "longitude": 76.9366},
    {"name": "Visakhapatnam", "district": "Visakhapatnam", "state": "Andhra Pradesh", "latitude": 17.6868, "longitude": 83.2185},
    {"name": "Vijayawada", "district": "NTR", "state": "Andhra Pradesh", "latitude": 16.5062, "longitude": 80.6480},
    {"name": "Coimbatore", "district": "Coimbatore", "state": "Tamil Nadu", "latitude": 11.0168, "longitude": 76.9558},
    {"name": "Madurai", "district": "Madurai", "state": "Tamil Nadu", "latitude": 9.9252, "longitude": 78.1198},
    {"name": "Guwahati", "district": "Kamrup Metropolitan", "state": "Assam", "latitude": 26.1445, "longitude": 91.7362},
    {"name": "Shillong", "district": "East Khasi Hills", "state": "Meghalaya", "latitude": 25.5788, "longitude": 91.8933},
    {"name": "Agartala", "district": "West Tripura", "state": "Tripura", "latitude": 23.8315, "longitude": 91.2868},
    {"name": "Imphal", "district": "Imphal West", "state": "Manipur", "latitude": 24.8170, "longitude": 93.9368},
    {"name": "Panaji", "district": "North Goa", "state": "Goa", "latitude": 15.4909, "longitude": 73.8278}
]


class CityItem(BaseModel):
    name: str
    district: str
    state: str
    latitude: float
    longitude: float
    country: str = "India"
    active_events_count: int = 0
    latest_event_category: Optional[str] = None
    latest_event_severity: Optional[str] = None


class CitiesResponse(BaseModel):
    cities: list[CityItem]
    total: int


def _get_configured_cities():
    for p in CANDIDATE_PATHS:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    cities = [
                        {
                            "name": c["name"],
                            "district": c.get("district", c["name"]),
                            "state": c.get("state", "India"),
                            "latitude": c.get("lat", c.get("latitude")),
                            "longitude": c.get("lon", c.get("longitude")),
                        }
                        for c in cfg.get("weather_api", {}).get("cities", [])
                    ]
                    if cities:
                        return cities
            except Exception:
                pass
    return ALL_DEFAULT_CITIES


@router.get("/cities", response_model=CitiesResponse)
def list_cities():
    """List all registered Indian meteorological monitoring hubs and active event counts."""
    base_cities = _get_configured_cities()
    city_stats: dict[str, dict] = {}

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT city, COUNT(*) as cnt,
                           (ARRAY_AGG(event_category ORDER BY last_seen DESC))[1] as latest_cat,
                           (ARRAY_AGG(severity ORDER BY last_seen DESC))[1] as latest_sev
                    FROM canonical_events
                    WHERE city IS NOT NULL
                    GROUP BY city;
                """)
                for row in cur.fetchall():
                    c_name, cnt, lat_cat, lat_sev = row
                    city_stats[c_name.lower()] = {
                        "count": cnt,
                        "category": lat_cat,
                        "severity": lat_sev,
                    }
    except Exception:
        pass

    results = []
    for c in base_cities:
        stats = city_stats.get(c["name"].lower(), {})
        results.append(CityItem(
            name=c["name"],
            district=c["district"],
            state=c["state"],
            latitude=c["latitude"],
            longitude=c["longitude"],
            country="India",
            active_events_count=stats.get("count", 0),
            latest_event_category=stats.get("category"),
            latest_event_severity=stats.get("severity"),
        ))

    return CitiesResponse(cities=results, total=len(results))

