"""
SIH26069 — Train and Export Production Model Artifact
Trains TF-IDF + LogisticRegression pipeline matching 05_AI_ML_SPEC.md
and exports to models/event_classifier/model.pkl.
"""

from __future__ import annotations

import json
import joblib
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
sys_ml = REPO_ROOT / "services" / "ml"
import sys
if str(sys_ml) not in sys.path:
    sys.path.insert(0, str(sys_ml))

from classifier.rules import VALID_CATEGORIES, KEYWORD_DICT

# Comprehensive corpus per category based on weather taxonomy and smoke test cases
SAMPLES_PER_CATEGORY = {
    "flood": [
        "Flash flood submerged roads and waterlogged streets",
        "Waterlogging and urban flood reported across Kurla Mumbai",
        "Submerged low-lying areas due to flash flooding inundation",
        "Heavy overflow from river causing flood waters in city",
        "Streets waterlogged with two feet of flood water",
        "Severe flooding on submerged roads",
        "Urban inundation and flash flood alert issued",
        "People evacuated from flooded localities water logging",
    ],
    "cyclone": [
        "Cyclone approaching coastal areas with strong winds",
        "Very severe cyclonic storm making landfall on coast",
        "Cyclone warning issued for coastal districts",
        "Cyclonic vortex system advancing towards coastal belt",
        "Severe cyclonic winds and storm surge warning",
        "Super cyclone landfall alert issued by meteorological department",
    ],
    "fog": [
        "Dense fog reducing visibility to near zero",
        "Low visibility due to dense morning fog on highway",
        "Thick fog blanket covers airport runway delayed flights",
        "Zero visibility observed in dense fog conditions",
        "Heavy mist and dense fog disrupting morning traffic",
    ],
    "heatwave": [
        "Heatwave conditions with temperature above 44 degrees",
        "Nagpur recorded 44.2C severe heatwave conditions",
        "Extreme heat wave alert with scorching temperatures",
        "Severe heatwave warning issued maximum temperature 45C",
        "Abnormal thermal anomaly and heatwave across district",
    ],
    "hailstorm": [
        "Hailstones damage crops in multiple districts",
        "Severe hailstorm and large hailstones reported in Nashik",
        "Hail storm activity with hail damaging vehicles and roofs",
        "Torrential hail stones hitting agricultural fields",
        "Hailstorm accompanied by sudden squall",
    ],
    "thunderstorm": [
        "Severe thunderstorm with thunder reported across the region",
        "Thunderstorm activity in district with lightning and rain",
        "Thunder storm with gusty squalls and heavy thunder",
        "Electrical storm with thunder rumbles and convective showers",
        "Severe thunderstorm alert with squalls",
    ],
    "strong_wind": [
        "Strong gusty winds uprooting trees",
        "High winds and gale force squalls damaging power lines",
        "Severe gusty wind blowing tin roofs off structures",
        "Gale force winds observed along coastal belt",
        "Strong winds recorded exceeding 65 kmph",
    ],
    "dust_storm": [
        "Dust storm reduces visibility on highways",
        "Severe duststorm and particulate front blinding motorists",
        "Blinding dust storm swept across desert highway",
        "Duststorm activity with brownout conditions",
        "Sudden dust storm with sand squall",
    ],
    "rainfall": [
        "Light rain and drizzle expected in the afternoon",
        "Scattered light rain showers observed this morning",
        "Gentle drizzle and intermittent light rain in the city",
        "Passing rain showers with light precipitation",
        "Moderate rain and intermittent drizzle",
    ],
    "heavy_rainfall": [
        "Torrential rain and very heavy rainfall recorded in district",
        "Heavy rainfall caused massive downpour and cloudburst",
        "Extreme deluge with heavy rain recording 120mm in 2 hours",
        "Continuous heavy rainfall alert issued for the state",
        "Torrential downpour with heavy rain warning",
    ],
    "lightning": [
        "Dangerous lightning strike damaged transmission tower",
        "Fatal lightning strike reported in rural area during storm",
        "Cloud-to-ground lightning flashes observed repeatedly",
        "Severe lightning strike killed cattle in open field",
        "Intense lightning electrical discharge damaged building",
    ],
    "other": [
        "Clear blue skies and sunny weather throughout the day",
        "Normal calm conditions with no weather anomalies",
        "Pleasant afternoon with mild temperatures and dry air",
        "Routine meteorological observation with fair weather",
        "Dry weather expected with no significant weather events",
    ],
}

def train_and_export():
    texts = []
    labels = []

    for cat, samples in SAMPLES_PER_CATEGORY.items():
        for sample in samples:
            texts.append(" ".join(sample.split()))
            labels.append(cat)

    # Also augment with keyword dictionary phrases
    for cat, kw_data in KEYWORD_DICT.items():
        if cat in VALID_CATEGORIES:
            for phrase in kw_data.get("phrases", []):
                texts.append(phrase)
                labels.append(cat)
            for word in kw_data.get("single", []):
                texts.append(f"weather alert {word} reported")
                labels.append(cat)

    print(f"Training dataset size: {len(texts)} samples across {len(set(labels))} categories")

    # Build Pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
            max_features=10000,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            C=10.0,
            max_iter=1000,
            random_state=42,
            class_weight="balanced",
        )),
    ])

    pipeline.fit(texts, labels)

    output_dir = REPO_ROOT / "models" / "event_classifier"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "model.pkl"
    joblib.dump(pipeline, model_path)
    print(f"Exported model pipeline to: {model_path}")

    # Also export legacy joblib files for compatibility
    joblib.dump(pipeline, output_dir / "classifier_pipeline.joblib")
    joblib.dump(pipeline.named_steps["clf"], output_dir / "classifier.joblib")
    joblib.dump(pipeline.named_steps["tfidf"], output_dir / "vectorizer.joblib")

    print("Model generation completed successfully.")

if __name__ == "__main__":
    train_and_export()
