"""
Unit tests for robust geolocation and fallback handling in common.py.
Uses standard Python assertions (no pytest dependency required).

Verifies:
1. Mumbai event text resolves correctly
2. Nagpur event text resolves correctly
3. Nashik event text resolves correctly
4. Indian event with coordinates but no city name preserves coordinates and country='India'
5. Foreign event preserves global coordinates, sets country='International', and NEVER assigns Mumbai
6. Event with no coordinates and no city name sets None rather than guessing Mumbai
7. Malformed coordinates are safely discarded without crashing
"""

import sys
import os

# Add parent directory to path so imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.common import infer_city, is_in_india, safe_coord, make_event, CITIES


def test_1_mumbai_event_text():
    text = "Heavy rainfall and flooding reported across Mumbai suburban rail tracks."
    assert infer_city(text) == "Mumbai", f"Expected Mumbai, got {infer_city(text)}"
    event = make_event("test", "test_source", "test_001", text)
    loc = event["location"]
    assert loc["city"] == "Mumbai"
    assert loc["district"] == "Mumbai City"
    assert loc["state"] == "Maharashtra"
    assert loc["country"] == "India"
    assert abs(loc["latitude"] - 19.0760) < 0.01
    assert abs(loc["longitude"] - 72.8777) < 0.01


def test_2_nagpur_event_text():
    text = "Heatwave alert issued for Nagpur as temperatures soar past 44 degrees."
    assert infer_city(text) == "Nagpur", f"Expected Nagpur, got {infer_city(text)}"
    event = make_event("test", "test_source", "test_002", text)
    loc = event["location"]
    assert loc["city"] == "Nagpur"
    assert loc["district"] == "Nagpur"
    assert loc["state"] == "Maharashtra"
    assert loc["country"] == "India"
    assert abs(loc["latitude"] - 21.1458) < 0.01
    assert abs(loc["longitude"] - 79.0882) < 0.01


def test_3_nashik_event_text():
    text = "Hailstorm damages vineyard crops in Nashik rural belt."
    assert infer_city(text) == "Nashik", f"Expected Nashik, got {infer_city(text)}"
    event = make_event("test", "test_source", "test_003", text)
    loc = event["location"]
    assert loc["city"] == "Nashik"
    assert loc["district"] == "Nashik"
    assert loc["state"] == "Maharashtra"
    assert loc["country"] == "India"
    assert abs(loc["latitude"] - 19.9975) < 0.01
    assert abs(loc["longitude"] - 73.7898) < 0.01


def test_4_indian_event_with_coords_no_city():
    # Coordinates in Odisha / Bay of Bengal coast (lat: 19.8135, lon: 85.8312)
    lat, lon = 19.8135, 85.8312
    assert is_in_india(lat, lon) is True

    text = "High tidal waves observed along eastern coastal embankment."
    # Text does not contain Mumbai, Nagpur, or Nashik
    assert infer_city(text) is None

    event = make_event("rss", "gdacs", "tc_india_01", text, latitude=lat, longitude=lon)
    loc = event["location"]
    assert loc["latitude"] == lat
    assert loc["longitude"] == lon
    assert loc["country"] == "India"
    # Must NOT have been overwritten with Mumbai!
    assert loc["city"] != "Mumbai"
    assert loc["district"] != "Mumbai City"


def test_5_foreign_event_preserves_coordinates_no_mumbai():
    # Tropical Cyclone Norbert at (16.5, -119.3) in Pacific Ocean
    lat, lon = 16.5, -119.3
    assert is_in_india(lat, lon) is False

    text = "Green notification for tropical cyclone NORBERT-26. Population affected is 0."
    assert infer_city(text) is None

    event = make_event("rss", "gdacs", "TC1001320", text, latitude=lat, longitude=lon)
    loc = event["location"]
    assert loc["latitude"] == 16.5
    assert loc["longitude"] == -119.3
    assert loc["country"] == "International"
    # MUST NOT be assigned to Mumbai!
    assert loc["city"] is None
    assert loc["district"] is None
    assert loc["state"] is None


def test_6_event_with_no_coords_and_no_city_remains_unknown():
    text = "General advisory: stay hydrated during hot afternoon hours."
    assert infer_city(text) is None

    event = make_event("website", "advisory", "adv_001", text)
    loc = event["location"]
    # NEVER default to Mumbai!
    assert loc["city"] is None
    assert loc["district"] is None
    assert loc["state"] is None
    assert loc["latitude"] is None
    assert loc["longitude"] is None


def test_7_malformed_coordinates_handled_gracefully():
    text = "Some random bulletin without location"
    # String non-numeric coordinates
    event1 = make_event("rss", "test", "bad_01", text, latitude="invalid_lat", longitude="bad_lon")
    loc1 = event1["location"]
    assert loc1["latitude"] is None
    assert loc1["longitude"] is None
    assert loc1["city"] is None

    # Out-of-range coordinates (> 90 lat or > 180 lon)
    event2 = make_event("rss", "test", "bad_02", text, latitude=999.0, longitude=999.0)
    loc2 = event2["location"]
    assert loc2["latitude"] is None
    assert loc2["longitude"] is None
    assert loc2["city"] is None


if __name__ == "__main__":
    test_1_mumbai_event_text()
    test_2_nagpur_event_text()
    test_3_nashik_event_text()
    test_4_indian_event_with_coords_no_city()
    test_5_foreign_event_preserves_coordinates_no_mumbai()
    test_6_event_with_no_coords_and_no_city_remains_unknown()
    test_7_malformed_coordinates_handled_gracefully()
    print("ALL 7 GEOLOCATION TESTS PASSED SUCCESSFULLY!")
