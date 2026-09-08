"""Shared source-adapter normalization helpers."""
import hashlib, re
from datetime import datetime, timezone
from normaliser.canonical_event import build_canonical_event

CITIES={"Mumbai":(19.076,72.878,"Mumbai City","Maharashtra"),"Nagpur":(21.146,79.088,"Nagpur","Maharashtra"),"Nashik":(19.998,73.789,"Nashik","Maharashtra")}
KEYWORDS=[("cyclone",("cyclone","hurricane","typhoon")),("flood",("flood","flooding","waterlogging","inundation","submerged")),("heavy_rainfall",("heavy rain","torrential","downpour","cloudburst")),("hailstorm",("hail","hailstorm")),("thunderstorm",("thunderstorm","thunder storm")),("lightning",("lightning","lightning strike")),("heatwave",("heatwave","heat wave","extreme heat")),("strong_wind",("strong wind","gust","gale")),("dust_storm",("dust storm","sandstorm")),("fog",("dense fog","fog","mist")),("rainfall",("rain","rainfall","showers"))]

def infer_category(text):
    t=text.lower()
    for cat, words in KEYWORDS:
        if any(w in t for w in words): return cat
    return "other"

def infer_city(text):
    for city in CITIES:
        if re.search(r"\b"+re.escape(city)+r"\b", text, re.I): return city
    return "Mumbai"

def make_event(source_type, source_name, source_id, text, timestamp=None, url=None, category=None, severity="moderate"):
    city=infer_city(text); lat,lon,district,state=CITIES[city]
    return build_canonical_event(source_type, source_name, source_id, text[:2000], category or infer_category(text), {"latitude":lat,"longitude":lon,"city":city,"district":district,"state":state,"country":"India"}, timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), source_url=url, severity=severity)
