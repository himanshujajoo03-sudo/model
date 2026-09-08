# Weather Intelligence Big Data AI/ML Package

> **Project:** SIH26069 — National Weather Big Data Analytics Platform  
> **Specification:** `05_AI_ML_SPEC.md` v1.2  
> **Status:** Production Ready  

---

## 1. Overview & Architecture

This package provides the complete, deterministic, lightweight AI/ML intelligence layer for weather big data stream processing. It is designed as a direct Python library imported inside Apache Spark Structured Streaming workers (no external microservice latency or GPU overhead).

### Three-Stage Training & Inference Architecture (§19)

```
                    MODEL DEVELOPMENT
                           │
             ┌─────────────┴─────────────┐
             ↓                           ↓
      Jupyter / Colab              Project training/
      experimentation              reproducible scripts
             │                           │
             └─────────────┬─────────────┘
                           ↓
                    Trained Model
                           ↓
                   Model Artifact (.pkl)
                           ↓
════════════════════════════════════════════
                     RUNTIME
════════════════════════════════════════════
                           ↓
                        Kafka
                           ↓
                  Spark Streaming
                           ↓
             Validation / Cleaning
                           ↓
                 Normalisation
                           ↓
                Feature Preparation
                           ↓
             load MODEL_PATH → sklearn Pipeline
                           ↓
                  Confidence Check
                    ↙           ↘
          ≥ threshold      < threshold /
               ↓           model failure
          ML result            ↓
                         Rule-based fallback
                    ↘           ↙
                  Final classification
                           ↓
                    weather.events
```

---

## 2. Core AI/ML Components

| Component | Function Signature | Method & Rationale | Output Fields |
|---|---|---|---|
| **Event Classification** | `classify_event(description, category_hint)` | Rule-based (English/Hindi/Marathi), Trained TF-IDF + LogisticRegression, or Hybrid | `ai.classified_category`<br>`ai.classification_confidence` |
| **Credibility Scoring** | `score_credibility(event, recent_events)` | Multi-factor weighted score: Source Trust (0.30), Corroboration (0.25), Weather Agreement (0.20), Temporal (0.10), Spatial (0.10), Quality (0.05) | `ai.credibility_score`<br>`ai.credibility_reasons` |
| **Duplicate Detection** | `compute_duplicate_score(current, recent_events)` | Weighted Jaccard text similarity (0.30), Source ID match (0.20), URL match (0.15), Category match (0.15), Time delta (0.10), Geo distance (0.10) | `ai.duplicate_score` |
| **Event Clustering** | `assign_cluster(event, active_clusters)` | Spatial-temporal clustering (Radius: $\le 3.0\text{ km}$, Time window: $\le 30\text{ min}$, Max size: 50, Compatible categories) | `ai.cluster_id` |
| **Explainability Engine** | `generate_reasons(factors, event)` | Deterministic, evidence-grounded templates with zero fabricated claims | `ai.credibility_reasons` |

---

## 3. Data Storage & Formatting Guide

The data ingestion engine automatically discovers, parses, validates, and cleans **any file placed in the `data/` directory**.

### 3.1 Folder Structure
```
data/
├── training/            # Primary location for training CSVs / JSONs
│   └── training_data.csv
├── raw/                 # Raw ingested event dumps from external sources
│   └── weather_events.json
├── incoming/            # New batch feeds or citizen/API data drops
│   ├── cleaned_weather_data.json
│   └── weather_events.json
└── processed/           # (Auto-generated) Normalized & deduplicated dataset
    └── cleaned_training_data.csv
```

### 3.2 Supported Formats

#### Option A: CSV Format (`.csv`)
Place any CSV file in `data/training/`, `data/incoming/`, or `data/`. Supported column headers:
- **Text column**: `text`, `description`, `event_description`, `report`, or `content`
- **Category column**: `category`, `event_type`, `label`, `category_label`, or `type`

Example CSV:
```csv
text,category
"Severe flooding and submerged roads near Kurla Mumbai",flood
"Torrential downpour with record rainfall recorded across Nashik",heavy_rainfall
"Extreme heatwave warning issued as temperatures cross 44C in Nagpur",heatwave
"High cyclonic winds damaged coastal power lines",cyclone
"Dense fog reducing visibility below 50 meters on highway",fog
```

#### Option B: JSON Format (`.json`)
Place any JSON file in `data/incoming/`, `data/raw/`, or `data/training/`. Supported structures:
- **Envelope JSON with `events` array**:
```json
{
  "generated_at": "2026-09-01T10:00:00Z",
  "events": [
    {
      "event_id": "evt-101",
      "description": "Waterlogging and flooded roads reported across low-lying areas",
      "event_type": "flooding"
    },
    {
      "event_id": "evt-102",
      "description": "Thunderstorm with lightning strikes in Pune district",
      "event_type": "thunderstorm"
    }
  ]
}
```
- **Top-level JSON list**:
```json
[
  {
    "description": "Scorching daytime heatwave conditions in Nagpur",
    "category": "heatwave"
  }
]
```

### 3.3 Supported Category Labels & Automatic Canonicalization

The 12 official taxonomy categories defined in `05_AI_ML_SPEC.md §4.1`:
```
rainfall          heavy_rainfall       flood
thunderstorm      lightning            heatwave
fog               dust_storm           strong_wind
hailstorm         cyclone              other
```

The data pipeline **automatically maps common variants** to the canonical category:
- `flooding`, `waterlogging`, `inundation` $\rightarrow$ `flood`
- `rain`, `shower`, `showers` $\rightarrow$ `rainfall`
- `heavy rain`, `torrential_rain` $\rightarrow$ `heavy_rainfall`
- `storm`, `thunder`, `thunder_storm` $\rightarrow$ `thunderstorm`
- `wind`, `high_winds`, `gale` $\rightarrow$ `strong_wind`
- `hail`, `hail_storm` $\rightarrow$ `hailstorm`
- `cyclonic`, `typhoon`, `hurricane` $\rightarrow$ `cyclone`
- `extreme_heat`, `heat` $\rightarrow$ `heatwave`
- `haze`, `smog`, `mist` $\rightarrow$ `fog`
- `dust`, `sandstorm` $\rightarrow$ `dust_storm`

---

## 4. Automated File Detection & Real-Time Retraining

You have **two ways** to detect new incoming files and retrain:

### Option A: Continuous Automated Watcher (Real-Time Auto-Retrain)
Run the real-time background watcher:
```powershell
python training/watch.py
```
**How it works:**
1. Continuously monitors `data/incoming/`, `data/training/`, and `data/raw/`.
2. The instant you paste, move, or save a new `.csv` or `.json` file into `data/incoming/`, the watcher automatically detects it.
3. It immediately runs data preparation, fits the updated model, evaluates metrics, and hot-updates `models/event_classifier/model.pkl`.

### Option B: Manual / CI Retraining Command
Whenever you want to trigger training directly:
```powershell
# 1. Scans data/ and prepares cleaned dataset
python training/prepare_data.py

# 2. Retrains the model and saves artifacts
python training/train.py

# 3. Runs comparative evaluation against baseline
python training/evaluate.py
```

---

## 5. How to Test the Entire ML Package

### Run Full Test Suite
Run all 41 automated tests:
```powershell
pytest -v
```

### Run Tests by Component
```powershell
# 1. Test Event Classifier (All 12 categories, Hindi/Marathi multilingual, hints, fallbacks)
pytest tests/test_classifier.py -v

# 2. Test Credibility Scorer (Source trust, corroboration, weather agreement, spatial/temporal)
pytest tests/test_credibility.py -v

# 3. Test Duplicate Detector (Identical reports, Jaccard text overlap, distance/time decay)
pytest tests/test_dedup.py -v

# 4. Test Event Clusterer (Spatial-temporal grouping, radius limits, representative selection)
pytest tests/test_clustering.py -v

# 5. Test Explainability (Deterministic reasons, no fabricated evidence)
pytest tests/test_explainability.py -v

# 6. Test Training & Retraining Pipeline (Data preparation, pipeline fitting, watcher detection)
pytest tests/test_training_pipeline.py -v

# 7. Test Demo Scenarios A through E (§26)
pytest tests/test_demo_scenarios.py -v
```

---

## 6. Demo Scenarios Verification (§26)

All 5 core demo scenarios are verified via `tests/test_demo_scenarios.py`:

| Scenario | Name | Key Verification |
|---|---|---|
| **Scenario A** | **Mumbai Flood** (Multi-Source Corroboration) | 5 reports from Open-Meteo, NDTV, Citizen, Social, and IMD correctly classify as `flood`/`heavy_rainfall`, cluster together within 3 km, and boost credibility score to $\ge 0.75$ via multi-source corroboration. |
| **Scenario B** | **Nagpur Heatwave** (API-Dominated) | Weather API and RSS reports with extreme temperatures classify as `heatwave` ($\ge 0.75$ confidence) with high credibility. |
| **Scenario C** | **Nashik Hailstorm** (Mixed Sources) | Mixed citizen and weather observations cluster together with compatible categories and high confidence. |
| **Scenario D** | **Duplicate Reports** | 3 near-identical reports from the same source within 3 minutes are flagged with duplicate score $\ge 0.85$. |
| **Scenario E** | **Suspicious Report** | Uncorroborated report from low-trust source with misaligned coordinates is flagged with low credibility ($\le 0.45$) and explicit explanation reasons. |

---

---

## 7. Multilingual Support & Testing Guide

This package provides native support for multiple languages (including **English, Hindi, Marathi**, and other Unicode Indic/World scripts).

### Architecture Overview
Multilingual processing is integrated into two primary modules:
- **Text Normalization (`utils/text.py`)**: Handles Unicode NFKC normalization and preserves word characters across scripts using Python's Unicode flag (`re.UNICODE`).
- **Feature Extraction & Classification (`training/train.py`, `classifier/`)**: Utilizes `scikit-learn`'s `TfidfVectorizer` with Unicode-aware token patterns (`token_pattern=r"(?u)\b\w+\b"`) alongside rule-based fallback keyword matching.

### How to Test Multilingual Support
All multilingual tests are located in `tests/test_classifier.py`. They validate correct classification of Hindi and Marathi event descriptions (e.g., heatwaves, thunderstorms, cyclones, heavy rainfall).

Run specifically the classifier tests (including Hindi and Marathi multilingual test cases):
```bash
pytest tests/test_classifier.py -v
```

### Training on Multilingual Data via `data/incoming/`
You can train the classifier on any new dataset (in any language) by placing your CSV or JSON files into the `data/incoming/` directory.

#### Automated Real-Time Watcher & Retrainer
The repository includes an automated file watcher (`training/watch.py`) that continuously monitors `data/incoming/`, `data/training/`, and `data/raw/` for new or modified files.

1. **Start the Watcher:**
   ```bash
   python training/watch.py
   ```
2. **Add Your Multilingual Data File:** Drop any `.csv` or `.json` file containing your labeled training data into `data/incoming/`. 

**Example JSON (`data/incoming/my_multilingual_data.json`):**
```json
[
  {
    "text": "भारी बारिश के कारण बाढ़ की स्थिति",
    "category": "heavy_rainfall"
  },
  {
    "text": "मुसळधार पाऊस आणि पूर परिस्थिती",
    "category": "heavy_rainfall"
  },
  {
    "text": "Severe flooding on submerged roads in Mumbai",
    "category": "flood"
  }
]
```

**Example CSV (`data/incoming/my_multilingual_data.csv`):**
```csv
text,category
"भारी बारिश के कारण बाढ़ की स्थिति","heavy_rainfall"
"मुसळधार पाऊस आणि पूर परिस्थिती","heavy_rainfall"
"Severe flooding on submerged roads in Mumbai","flood"
```

#### Manual Retraining Alternative
```bash
python training/train.py
```


## 7. How to Switch Classifier Backends

You can switch the active classifier backend seamlessly without changing any Spark or consumer code:

### Option 1: Rule-Based Backend (Default / Stage 1)
```powershell
$env:CLASSIFIER_BACKEND="rule_based"
```

### Option 2: Trained Supervised Model (Stage 2)
```powershell
$env:CLASSIFIER_BACKEND="trained"
$env:MODEL_PATH="models/event_classifier/model.pkl"
```

### Option 3: Hybrid Backend (Confidence-Gated Fallback)
```powershell
$env:CLASSIFIER_BACKEND="hybrid"
$env:MODEL_CONFIDENCE_THRESHOLD="0.75"
```
In hybrid mode, the trained model is used if confidence $\ge 0.75$; otherwise, the system automatically falls back to deterministic rule-based matching.

---

## 8. Package Directory Structure

```
services/ml/ (or d:/ML/ml/)
│
├── config/
│   ├── ml_config.yaml              # Global weights, thresholds, and cluster parameters
│   ├── source_trust.yaml           # Baseline source trust ratings and provider overrides
│   └── india_cities.json           # Bounding boxes for Indian cities (Mumbai, Nagpur, Nashik, etc.)
│
├── classifier/
│   ├── __init__.py
│   ├── interface.py                # BaseClassifier abstract interface
│   ├── event_classifier.py         # classify_event() entry point with backend dispatch
│   ├── rule_based_classifier.py    # Deterministic keyword NLP classifier
│   ├── trained_classifier.py       # scikit-learn Pipeline inference classifier
│   ├── hybrid_classifier.py        # Confidence-gated hybrid classifier
│   └── rules.py                    # Taxonomy (12 categories) & Multilingual keyword dictionaries
│
├── models/
│   └── event_classifier/
│       ├── model.pkl               # Trained scikit-learn Pipeline artifact
│       └── metadata.json           # Model version, metrics, parameters, training date
│
├── training/
│   ├── __init__.py
│   ├── prepare_data.py             # Data cleaning, taxonomy validation, deduplication
│   ├── train.py                    # Offline reproducible training & retraining script
│   ├── evaluate.py                 # Comparative F1 evaluation against rule baseline
│   └── watch.py                    # Real-time automated watcher & retrainer
│
├── credibility/
│   ├── __init__.py
│   ├── credibility_scorer.py       # score_credibility() multi-factor engine
│   └── source_weights.py           # Independent corroboration and trust loading
│
├── dedup/
│   ├── __init__.py
│   └── duplicate_detector.py       # compute_duplicate_score() with Jaccard & spatial decay
│
├── clustering/
│   ├── __init__.py
│   └── event_clusterer.py          # assign_cluster() spatial-temporal grouping
│
├── explainability/
│   ├── __init__.py
│   └── reason_generator.py         # generate_reasons() evidence-grounded templates
│
├── utils/
│   ├── __init__.py
│   ├── text.py                     # Unicode NFKC text normalization & Jaccard similarity
│   ├── geo.py                      # Haversine distance & city bounding box validator
│   └── time_utils.py               # ISO-8601 parsing & minute delta calculations
│
└── tests/
    ├── fixtures/                   # JSON fixtures for Scenarios A–E & edge cases
    ├── test_classifier.py
    ├── test_credibility.py
    ├── test_dedup.py
    ├── test_clustering.py
    ├── test_explainability.py
    ├── test_training_pipeline.py
    └── test_demo_scenarios.py
```
#   S I H - A I - M L  
 