"""Shared source-adapter normalization helpers with robust geographic handling."""
import hashlib
import re
from datetime import datetime, timezone
from normaliser.canonical_event import build_canonical_event

# Supported Indian cities with verified centroid coordinates
CITIES = {
    "Mumbai": (19.0760, 72.8777, "Mumbai City", "Maharashtra"),
    "Nagpur": (21.1458, 79.0882, "Nagpur", "Maharashtra"),
    "Nashik": (19.9975, 73.7898, "Nashik", "Maharashtra"),
    "Pune": (18.5204, 73.8567, "Pune", "Maharashtra"),
    "Delhi": (28.6139, 77.2090, "New Delhi", "Delhi"),
    "Agra": (27.1767, 78.0081, "Agra", "Uttar Pradesh"),
    "Bengaluru": (12.9716, 77.5946, "Bengaluru Urban", "Karnataka"),
    "Chennai": (13.0827, 80.2707, "Chennai", "Tamil Nadu"),
    "Kolkata": (22.5726, 88.3639, "Kolkata", "West Bengal"),
    "Hyderabad": (17.3850, 78.4867, "Hyderabad", "Telangana"),
    "Ahmedabad": (23.0225, 72.5714, "Ahmedabad", "Gujarat"),
    "Surat": (21.1702, 72.8311, "Surat", "Gujarat"),
    "Jaipur": (26.9124, 75.7873, "Jaipur", "Rajasthan"),
    "Lucknow": (26.8467, 80.9462, "Lucknow", "Uttar Pradesh"),
    "Varanasi": (25.3176, 82.9739, "Varanasi", "Uttar Pradesh"),
    "Kanpur": (26.4499, 80.3319, "Kanpur Nagar", "Uttar Pradesh"),
    "Chandigarh": (30.7333, 76.7794, "Chandigarh", "Chandigarh"),
    "Amritsar": (31.6340, 74.8723, "Amritsar", "Punjab"),
    "Shimla": (31.1048, 77.1734, "Shimla", "Himachal Pradesh"),
    "Dehradun": (30.3165, 78.0322, "Dehradun", "Uttarakhand"),
    "Srinagar": (34.0837, 74.7973, "Srinagar", "Jammu and Kashmir"),
    "Bhopal": (23.2599, 77.4126, "Bhopal", "Madhya Pradesh"),
    "Indore": (22.7196, 75.8577, "Indore", "Madhya Pradesh"),
    "Patna": (25.5941, 85.1376, "Patna", "Bihar"),
    "Ranchi": (23.3441, 85.3096, "Ranchi", "Jharkhand"),
    "Bhubaneswar": (20.2961, 85.8245, "Khordha", "Odisha"),
    "Puri": (19.8135, 85.8312, "Puri", "Odisha"),
    "Raipur": (21.2514, 81.6296, "Raipur", "Chhattisgarh"),
    "Kochi": (9.9312, 76.2673, "Ernakulam", "Kerala"),
    "Thiruvananthapuram": (8.5241, 76.9366, "Thiruvananthapuram", "Kerala"),
    "Visakhapatnam": (17.6868, 83.2185, "Visakhapatnam", "Andhra Pradesh"),
    "Vijayawada": (16.5062, 80.6480, "NTR", "Andhra Pradesh"),
    "Coimbatore": (11.0168, 76.9558, "Coimbatore", "Tamil Nadu"),
    "Madurai": (9.9252, 78.1198, "Madurai", "Tamil Nadu"),
    "Guwahati": (26.1445, 91.7362, "Kamrup Metropolitan", "Assam"),
    "Shillong": (25.5788, 91.8933, "East Khasi Hills", "Meghalaya"),
    "Agartala": (23.8315, 91.2868, "West Tripura", "Tripura"),
    "Imphal": (24.8170, 93.9368, "Imphal West", "Manipur"),
    "Panaji": (15.4909, 73.8278, "North Goa", "Goa"),
}

# India geographic bounding box (including territorial waters and islands)
INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 38.0
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 98.0

KEYWORDS = [
    ("cyclone", ("cyclone", "hurricane", "typhoon")),
    ("flood", ("flood", "flooding", "waterlogging", "inundation", "submerged")),
    ("heavy_rainfall", ("heavy rain", "torrential", "downpour", "cloudburst")),
    ("hailstorm", ("hail", "hailstorm")),
    ("thunderstorm", ("thunderstorm", "thunder storm")),
    ("lightning", ("lightning", "lightning strike")),
    ("heatwave", ("heatwave", "heat wave", "extreme heat")),
    ("strong_wind", ("strong wind", "gust", "gale")),
    ("dust_storm", ("dust storm", "sandstorm")),
    ("fog", ("dense fog", "fog", "mist")),
    ("rainfall", ("rain", "rainfall", "showers")),
]


def is_in_india(lat: float, lon: float) -> bool:
    """Check if given coordinates fall inside India's geographic bounding box."""
    if lat is None or lon is None:
        return False
    return INDIA_LAT_MIN <= lat <= INDIA_LAT_MAX and INDIA_LON_MIN <= lon <= INDIA_LON_MAX


def safe_coord(val):
    """Safely convert coordinate to float, returning None on invalid/malformed input."""
    if val is None:
        return None
    try:
        f = float(val)
        return f
    except (ValueError, TypeError):
        return None


def infer_category(text):
    """Infer weather event category from text keywords."""
    if not text:
        return "other"
    t = text.lower()
    for cat, words in KEYWORDS:
        if any(w in t for w in words):
            return cat
    return "other"


def infer_city(text):
    """
    Search text for known Indian city names.
    Returns the matched city name (e.g. 'Mumbai', 'Nagpur', 'Nashik') if found,
    or None if no known city is matched.
    CRITICAL: Never defaults to Mumbai.
    """
    if not text:
        return None
    for city in CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE):
            return city
    return None


def make_event(
    source_type,
    source_name,
    source_id,
    text,
    timestamp=None,
    url=None,
    category=None,
    severity="moderate",
    latitude=None,
    longitude=None,
    city=None,
    district=None,
    state=None,
    country=None,
):
    """
    Build a Canonical Weather Event with robust geographic handling.
    - Preserves actual coordinates whenever available (including global/foreign coordinates).
    - If coordinates are outside India, sets country='International' (or metadata country)
      and does not force Indian city/district/state.
    - If no coordinates provided, checks text for known Indian cities.
    - If neither coordinates nor known city found, leaves location fields as None (unknown)
      rather than guessing.
    """
    text_snippet = (text or "")[:2000]
    lat = safe_coord(latitude)
    lon = safe_coord(longitude)

    # Validate coordinate range if provided
    if lat is not None and not (-90.0 <= lat <= 90.0):
        lat = None
    if lon is not None and not (-180.0 <= lon <= 180.0):
        lon = None

    resolved_city = city
    resolved_district = district
    resolved_state = state
    resolved_country = country

    if lat is not None and lon is not None:
        # Valid coordinates provided
        if is_in_india(lat, lon):
            resolved_country = resolved_country or "India"
            # If city not explicitly passed, attempt city match from text
            if not resolved_city:
                matched_city = infer_city(text_snippet)
                if matched_city:
                    resolved_city = matched_city
                    _, _, resolved_district, resolved_state = CITIES[matched_city]
        else:
            # Foreign / International event — preserve coordinates, do not force Indian administrative fields
            resolved_country = resolved_country or "International"
            resolved_city = city or None
            resolved_district = district or None
            resolved_state = state or None
    else:
        # No valid coordinates provided — attempt text inference for Indian cities
        matched_city = infer_city(text_snippet)
        if matched_city:
            resolved_city = matched_city
            lat, lon, resolved_district, resolved_state = CITIES[matched_city]
            resolved_country = "India"
        else:
            # Completely unknown location: do NOT guess Mumbai!
            lat = None
            lon = None
            resolved_city = None
            resolved_district = None
            resolved_state = None
            resolved_country = None

    location = {
        "latitude": lat,
        "longitude": lon,
        "city": resolved_city,
        "district": resolved_district,
        "state": resolved_state,
        "country": resolved_country or "India",
    }

    event_ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    cat = category or infer_category(text_snippet)

    return build_canonical_event(
        source_type=source_type,
        source_name=source_name,
        source_id=str(source_id),
        description=text_snippet,
        category=cat,
        location=location,
        timestamp=event_ts,
        source_url=url,
        severity=severity,
    )
