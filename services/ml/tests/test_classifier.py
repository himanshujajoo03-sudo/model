from __future__ import annotations

"""
Classification Engine Unit Tests (§25.1).
"""

import sys
from pathlib import Path
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from classifier.event_classifier import classify_event, is_high_confidence
from classifier.rule_based_classifier import RuleBasedClassifier
from classifier.rules import VALID_CATEGORIES


def test_classifier_import():
    assert callable(classify_event)


@pytest.mark.parametrize("text,expected_category", [
    ("Waterlogged and flooded roads in Kurla Mumbai", "flood"),
    ("Torrential rain and very heavy rainfall recorded in Nashik", "heavy_rainfall"),
    ("Light rain showers observed this morning", "rainfall"),
    ("Severe thunderstorm with electrical activity overnight", "thunderstorm"),
    ("Dangerous lightning strike damaged transmission tower", "lightning"),
    ("Extreme heatwave with temperature above 44 degrees in Nagpur", "heatwave"),
    ("Dense fog reducing morning visibility to 50m", "fog"),
    ("Severe dust storm with high sandy winds", "dust_storm"),
    ("Strong wind gusts damaged trees and roofs", "strong_wind"),
    ("Severe hailstorm with large hailstones destroying crops", "hailstorm"),
    ("Very severe cyclonic storm approaching coastal belt", "cyclone"),
    ("Unusual weather condition observed without specific incident", "other"),
])
def test_all_categories_classification(text, expected_category):
    result = classify_event(text)
    assert result["classified_category"] == expected_category
    assert result["classification_confidence"] > 0.40
    # Verify backward compatibility fields
    assert result["category"] == expected_category
    assert "confidence" in result


@pytest.mark.parametrize("text,expected_category", [
    ("भारी बारिश के कारण बाढ़ की स्थिति उत्पन्न हो गई", "heavy_rainfall"),
    ("नागपुर में अत्यधिक गर्मी और लू का प्रकोप", "heatwave"),
    ("आंधी और तूफान के साथ बिजली गिरने की संभावना", "thunderstorm"),
    ("तटीय क्षेत्रों में चक्रवात की चेतावनी", "cyclone"),
    ("सर्दियों में घना कोहरा छाया हुआ है", "fog"),
])
def test_hindi_multilingual_classification(text, expected_category):
    result = classify_event(text)
    assert result["classified_category"] == expected_category
    assert result["classification_confidence"] >= 0.50


@pytest.mark.parametrize("text,expected_category", [
    ("मुसळधार पाऊस आणि पूर परिस्थिती", "heavy_rainfall"),
    ("विदर्भात तीव्र उन्हाची लाट पसरली आहे", "heatwave"),
    ("वादळ आणि मेघगर्जना सुरू आहे", "thunderstorm"),
    ("नाशिक भागात जोरदार गारपीट झाली", "hailstorm"),
    ("चक्रीवादळ किनारपट्टीकडे सरकत आहे", "cyclone"),
])
def test_marathi_multilingual_classification(text, expected_category):
    result = classify_event(text)
    assert result["classified_category"] == expected_category
    assert result["classification_confidence"] >= 0.50


def test_empty_description_fallback_hint():
    result = classify_event("", category_hint="cyclone")
    assert result["classified_category"] == "cyclone"
    assert result["classification_confidence"] == 0.30


def test_none_description():
    result = classify_event(None)
    assert result["classified_category"] == "other"


def test_high_confidence_helper():
    assert is_high_confidence(0.85, threshold=0.80) is True
    assert is_high_confidence(0.65, threshold=0.80) is False