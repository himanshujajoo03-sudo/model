from __future__ import annotations

"""
Weather Taxonomy and Keyword Rule Dictionaries.
Derived from 05_AI_ML_SPEC.md §4.1, §4.4, §4.5, §6.1, §10.3.
Weather Taxonomy and Keyword Rule Dictionaries (§4.1, §4.4, §4.5, §6.1, §10.3).
Single source of truth for:
1. Canonical categories (12 taxonomy values)
2. Aliases and category canonicalization
3. Strict category validation
4. Symmetric category compatibility graph
5. Keyword dictionaries (English, Hindi, Marathi)
"""

import difflib
from typing import Optional

# §4.1 Allowed Categories (Exact 12 taxonomy values)
VALID_CATEGORIES = [
    "rainfall",
    "heavy_rainfall",
    "flood",
    "thunderstorm",
    "lightning",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_wind",
    "hailstorm",
    "cyclone",
    "other",
]

VALID_CATEGORIES_SET = set(VALID_CATEGORIES)

# §6.1 Priority Order (highest -> lowest)
CATEGORY_PRIORITY = [
    "cyclone",
    "flood",
    "heavy_rainfall",
    "hailstorm",
    "thunderstorm",
    "lightning",
    "heatwave",
    "strong_wind",
    "dust_storm",
    "fog",
    "rainfall",
    "other",
]

# Canonical Aliases mapping to standard 12 categories (§4.10)
TAXONOMY_ALIASES = {
    # Flood variants
    "flooding": "flood",
    "waterlogging": "flood",
    "water logging": "flood",
    "waterlogged": "flood",
    "inundation": "flood",
    "flash flood": "flood",
    "flash_flood": "flood",
    # Rainfall variants
    "rain": "rainfall",
    "shower": "rainfall",
    "showers": "rainfall",
    "light rain": "rainfall",
    "light_rain": "rainfall",
    "precipitation": "rainfall",
    "drizzle": "rainfall",
    # Heavy rainfall variants
    "heavy rain": "heavy_rainfall",
    "heavy_rain": "heavy_rainfall",
    "torrential rain": "heavy_rainfall",
    "torrential_rain": "heavy_rainfall",
    "cloudburst": "heavy_rainfall",
    "cloud burst": "heavy_rainfall",
    "downpour": "heavy_rainfall",
    # Thunderstorm variants
    "storm": "thunderstorm",
    "thunder": "thunderstorm",
    "thunder_storm": "thunderstorm",
    "thunder storm": "thunderstorm",
    "electrical storm": "thunderstorm",
    # Strong wind variants
    "wind": "strong_wind",
    "high winds": "strong_wind",
    "high_winds": "strong_wind",
    "gusty winds": "strong_wind",
    "gusty_wind": "strong_wind",
    "gale": "strong_wind",
    "squall": "strong_wind",
    # Hailstorm variants
    "hail": "hailstorm",
    "hail storm": "hailstorm",
    "hail_storm": "hailstorm",
    "hailstones": "hailstorm",
    # Cyclone variants
    "cyclonic": "cyclone",
    "cyclonic storm": "cyclone",
    "typhoon": "cyclone",
    "hurricane": "cyclone",
    "tropical storm": "cyclone",
    # Heatwave variants
    "heat": "heatwave",
    "extreme heat": "heatwave",
    "extreme_heat": "heatwave",
    "heat wave": "heatwave",
    "sweltering": "heatwave",
    # Fog variants
    "haze": "fog",
    "smog": "fog",
    "mist": "fog",
    "dense fog": "fog",
    # Dust storm variants
    "dust": "dust_storm",
    "sandstorm": "dust_storm",
    "sand storm": "dust_storm",
}


class InvalidCategoryError(ValueError):
    """Raised when an unknown or invalid category label is encountered."""
    def __init__(self, message: str, invalid_value: str | None = None, suggestions: list[str] | None = None):
        super().__init__(message)
        self.invalid_value = invalid_value
        self.suggestions = suggestions or []


def canonicalize_category(
    raw_cat: str | None,
    strict: bool = False,
    file_path: str | None = None,
    row_index: int | str | None = None
) -> Optional[str]:
    """
    Canonicalize a category string to one of the 12 official taxonomy categories.
    
    If strict=True, raises InvalidCategoryError for unknown values (NEVER maps to 'other').
    If strict=False, returns None for unknown/empty values (NEVER maps to 'other' unless raw_cat was 'other').
    """
    if raw_cat is None:
        if strict:
            loc = f" (file: {file_path}, row: {row_index})" if (file_path or row_index) else ""
            raise InvalidCategoryError(
                f"Missing or empty category label{loc}. Supported categories: {', '.join(VALID_CATEGORIES)}",
                invalid_value=None
            )
        return None

    cleaned = str(raw_cat).strip().lower()
    if not cleaned:
        if strict:
            loc = f" (file: {file_path}, row: {row_index})" if (file_path or row_index) else ""
            raise InvalidCategoryError(
                f"Empty category label{loc}. Supported categories: {', '.join(VALID_CATEGORIES)}",
                invalid_value=raw_cat
            )
        return None

    # Check exact match in valid categories
    if cleaned in VALID_CATEGORIES_SET:
        return cleaned

    # Check with underscore replacement
    clean_normalized = cleaned.replace("-", "_")
    if clean_normalized in VALID_CATEGORIES_SET:
        return clean_normalized

    # Check in aliases
    clean_space = cleaned.replace("-", " ").replace("_", " ")
    if clean_normalized in TAXONOMY_ALIASES:
        return TAXONOMY_ALIASES[clean_normalized]
    if clean_space in TAXONOMY_ALIASES:
        return TAXONOMY_ALIASES[clean_space]
    if cleaned in TAXONOMY_ALIASES:
        return TAXONOMY_ALIASES[cleaned]

    # Unknown category
    if strict:
        all_known = list(VALID_CATEGORIES) + list(TAXONOMY_ALIASES.keys())
        matches = difflib.get_close_matches(cleaned, all_known, n=3, cutoff=0.5)
        suggestion_str = f" Did you mean '{matches[0]}'?" if matches else ""
        loc = f" (file: {file_path}, row: {row_index})" if (file_path or row_index) else ""
        raise InvalidCategoryError(
            f"Invalid category '{raw_cat}'{loc}. Supported categories: {', '.join(VALID_CATEGORIES)}.{suggestion_str}",
            invalid_value=raw_cat,
            suggestions=matches
        )

    return None


def validate_category(
    raw_cat: str | None,
    file_path: str | None = None,
    row_index: int | str | None = None
) -> str:
    """Strict validation helper that returns the canonical category or raises InvalidCategoryError."""
    cat = canonicalize_category(raw_cat, strict=True, file_path=file_path, row_index=row_index)
    if cat is None:
        loc = f" (file: {file_path}, row: {row_index})" if (file_path or row_index) else ""
        raise InvalidCategoryError(
            f"Invalid category '{raw_cat}'{loc}. Supported categories: {', '.join(VALID_CATEGORIES)}",
            invalid_value=raw_cat
        )
    return cat


# §4.4 Keyword Dictionaries (English, Hindi, Marathi)
KEYWORD_DICT = {
    "flood": {
        "phrases": [
            "flash flood",
            "rising water",
            "submerged roads",
            "knee deep water",
            "knee-deep water",
            "water logging",
            "waterlogging",
            "water logged",
            "waterlogged",
            "पानी भरा",
            "डूबा हुआ",
            "पाण्याचा प्रवाह",
        ],
        "single": [
            "flood",
            "flooded",
            "flooding",
            "inundated",
            "submerged",
            "overflow",
            "बाढ़",
            "जलभराव",
            "पूर",
        ],
    },
    "heavy_rainfall": {
        "phrases": [
            "heavy rain",
            "heavy rainfall",
            "very heavy rainfall",
            "torrential rain",
            "extremely heavy rain",
            "intense rainfall",
            "record rainfall",
            "downpour",
            "cloud burst",
            "cloudburst",
            "भारी बारिश",
            "मूसलाधार बारिश",
            "मुसळधार पाऊस",
            "जड पाऊस",
        ],
        "single": [
            "torrential",
            "cloudburst",
        ],
    },
    "rainfall": {
        "phrases": [
            "light rain",
            "rain shower",
            "passing shower",
            "light showers",
            "rain showers",
        ],
        "single": [
            "rain",
            "rainfall",
            "raining",
            "showers",
            "shower",
            "drizzle",
            "precipitation",
            "बारिश",
            "वर्षा",
            "बूँदाबांदी",
            "पाऊस",
            "सरी",
        ],
    },
    "thunderstorm": {
        "phrases": [
            "lightning storm",
            "electrical storm",
            "thunder storm",
            "thunder and lightning",
            "बिजली गिरना",
            "मेघगर्जन",
        ],
        "single": [
            "thunderstorm",
            "thunder",
            "storm",
            "stormy",
            "तूफान",
            "आंधी",
            "वादळ",
        ],
    },
    "lightning": {
        "phrases": [
            "lightning strike",
            "lightning bolt",
            "thunderbolt",
            "lightning discharge",
            "lightning strikes",
            "गाजवीज",
        ],
        "single": [
            "lightning",
            "बिजली",
            "चमक",
        ],
    },
    "heatwave": {
        "phrases": [
            "heat wave",
            "extreme heat",
            "heat warning",
            "very hot",
            "temperature above 40",
            "temperature above 42",
            "temperature above 44",
            "temperature above 45",
            "severe heat",
            "heatwave conditions",
            "scorching heatwave",
            "extreme daytime heat",
            "गर्मी की लहर",
            "उन्हाची लाट",
            "अत्यधिक गर्मी",
            "अत्यधिक उकड",
        ],
        "single": [
            "heatwave",
            "scorching",
            "sweltering",
            "लू",
            "उष्माघात",
        ],
    },
    "fog": {
        "phrases": [
            "dense fog",
            "low visibility",
            "dense smog",
            "morning fog",
            "thick fog",
        ],
        "single": [
            "fog",
            "foggy",
            "misty",
            "mist",
            "smog",
            "haze",
            "कोहरा",
            "धुंध",
            "धुके",
        ],
    },
    "dust_storm": {
        "phrases": [
            "dust storm",
            "sandy winds",
            "dust devil",
            "sand storm",
            "रेत का तूफान",
        ],
        "single": [
            "sandstorm",
            "duststorm",
            "धूल",
        ],
    },
    "strong_wind": {
        "phrases": [
            "strong wind",
            "strong winds",
            "gusty winds",
            "high winds",
            "wind speed",
            "cyclonic winds",
            "तेज हवाएं",
            "जोराचा वारा",
        ],
        "single": [
            "gale",
            "gust",
            "gusts",
            "windy",
            "squall",
        ],
    },
    "hailstorm": {
        "phrases": [
            "ice pellets",
            "hail damage",
            "hail stone",
            "hail stones",
            "ओले गिरना",
        ],
        "single": [
            "hail",
            "hailstones",
            "hailstone",
            "hailstorm",
            "hailfall",
            "ओलावृष्टि",
            "ओले",
            "गाठणे",
            "गारपीट",
            "अंबरी",
        ],
    },
    "cyclone": {
        "phrases": [
            "tropical storm",
            "tropical depression",
            "very severe cyclonic storm",
            "cyclonic storm",
            "deep depression",
        ],
        "single": [
            "cyclone",
            "cyclonic",
            "typhoon",
            "hurricane",
            "चक्रवात",
            "चक्रीवादळ",
        ],
    },
    "other": {
        "phrases": [
            "unusual weather",
            "weather condition",
            "weather report",
        ],
        "single": [],
    },
}

# §10.3 / §4.5 Category Compatibility Map
CATEGORY_COMPATIBILITY = {
    "rainfall": {"rainfall", "heavy_rainfall", "flood"},
    "heavy_rainfall": {"rainfall", "heavy_rainfall", "flood", "thunderstorm"},
    "flood": {"rainfall", "heavy_rainfall", "flood"},
    "thunderstorm": {"thunderstorm", "lightning", "heavy_rainfall"},
    "lightning": {"thunderstorm", "lightning"},
    "heatwave": {"heatwave"},
    "fog": {"fog"},
    "dust_storm": {"dust_storm", "strong_wind"},
    "strong_wind": {"strong_wind", "cyclone", "dust_storm"},
    "hailstorm": {"hailstorm", "thunderstorm", "heavy_rainfall"},
    "cyclone": {"cyclone", "strong_wind", "heavy_rainfall", "flood"},
    "other": set(),  # "other" does not corroborate anything
}
# =====================================================================
# Symmetric Category Compatibility Graph (§10.3 / §4.5)
# Guarantee: A in COMPATIBILITY[B] <==> B in COMPATIBILITY[A]
# Note: "other" does not corroborate any category, not even itself.
# =====================================================================

_BASE_COMPATIBILITY_EDGES = [
    ("rainfall", "rainfall"),
    ("rainfall", "heavy_rainfall"),
    ("rainfall", "flood"),

    ("heavy_rainfall", "heavy_rainfall"),
    ("heavy_rainfall", "flood"),
    ("heavy_rainfall", "thunderstorm"),
    ("heavy_rainfall", "hailstorm"),
    ("heavy_rainfall", "cyclone"),

    ("flood", "flood"),
    ("flood", "cyclone"),

    ("thunderstorm", "thunderstorm"),
    ("thunderstorm", "lightning"),
    ("thunderstorm", "hailstorm"),

    ("lightning", "lightning"),

    ("heatwave", "heatwave"),

    ("fog", "fog"),

    ("dust_storm", "dust_storm"),
    ("dust_storm", "strong_wind"),

    ("strong_wind", "strong_wind"),
    ("strong_wind", "cyclone"),

    ("hailstorm", "hailstorm"),

    ("cyclone", "cyclone"),
]

# Build symmetric map dynamically
CATEGORY_COMPATIBILITY: dict[str, set[str]] = {cat: set() for cat in VALID_CATEGORIES}

for u, v in _BASE_COMPATIBILITY_EDGES:
    if u in CATEGORY_COMPATIBILITY and v in CATEGORY_COMPATIBILITY:
        CATEGORY_COMPATIBILITY[u].add(v)
        CATEGORY_COMPATIBILITY[v].add(u)


def categories_are_compatible(cat1: str | None, cat2: str | None) -> bool:
    """
    Check if two event categories are semantically compatible (§10.3).

    Guarantees symmetry: categories_are_compatible(A, B) == categories_are_compatible(B, A).
    Normalizes aliases and category names. Unknown categories safely return False.
    'other' never corroborates anything (returns False).
    """
    c1 = canonicalize_category(cat1, strict=False)
    c2 = canonicalize_category(cat2, strict=False)

    if not c1 or not c2:
        return False

    # "other" never corroborates
    if c1 == "other" or c2 == "other":
        return False

    if c1 == c2:
        return True

    # Check symmetric lookup
    return c2 in CATEGORY_COMPATIBILITY.get(c1, set())
