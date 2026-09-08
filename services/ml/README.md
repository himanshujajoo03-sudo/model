# Weather Intelligence Big Data AI/ML Package

> **Project:** SIH26069 — National Weather Big Data Analytics Platform  
> **Specification:** `05_AI_ML_SPEC.md` v1.2  
> **Status:** Hardened & Production Ready  

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
                    Candidate Model (models/candidates/)
                           ↓
               Evaluation & Acceptance Gate
                           ↓
               Atomic Production Deployment (models/event_classifier/)
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
                 Normalisation (NormalizedEvent)
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
| **Event Clustering** | `assign_cluster(event, active_clusters)` | Spatial-temporal clustering (Radius: $\le 3.0\text{ km}$, Time window: $\le 30\text{ min}$, Max size: 50, Symmetric compatible categories) | `ai.cluster_id` |
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

### 3.2 Supported Categories & Aliases

The 12 official taxonomy categories defined in `05_AI_ML_SPEC.md §4.1`:
```
rainfall          heavy_rainfall       flood
thunderstorm      lightning            heatwave
fog               dust_storm           strong_wind
hailstorm         cyclone              other
```

The pipeline automatically maps common aliases to canonical categories:
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

> [!IMPORTANT]
> **Strict Category Validation**: Unknown labels (such as `"banana"`) are explicitly **rejected** with an `InvalidCategoryError` detailing the filename, row index, and closest matching suggestion. Unknown labels are **never** silently converted to `"other"`.

---

## 4. Key Hardening & Architectural Guarantees

1. **Symmetric Category Compatibility**: For any category pair $(A, B)$, $A \leftrightarrow B$ is strictly equivalent to $B \leftrightarrow A$. Specifically resolves bidirectional compatibility for `cyclone` $\leftrightarrow$ `flood`, `heavy_rainfall` $\leftrightarrow$ `cyclone`, and `hailstorm` $\leftrightarrow$ `thunderstorm`.
2. **Coordinate 0 Support**: Numeric coordinates at the Equator and Prime Meridian `(0.0, 0.0)` are explicitly handled without falling back to defaults. Latitude must satisfy $-90 \le \text{lat} \le 90$ and longitude $-180 \le \text{lon} \le 180$.
3. **Timezone Standardization & Future Timestamp Guardrails**: All timestamps are standardized to timezone-aware UTC. Clock skew $\le 5$ minutes is tolerated; timestamps significantly in the future receive severe credibility penalties and are rejected from historical clustering.
4. **Data Leakage Auditing**: Training checks for exact text overlap across train, validation, and test splits prior to fitting.
5. **Small Dataset Split Protection**: Guardrails prevent stratified train/test split crashes when classes contain fewer than 3 samples.
6. **Atomic Deployment & Quality Gates**: Retrained models are staged in `models/candidates/` and promoted to `models/event_classifier/` only when validation and test criteria pass. Failed retrains will never destroy production models.
7. **Debounced Real-Time Watcher**: Ingestion file watchers wait for file writing activity to settle (`debounce_seconds: 2.0`) before triggering a single, locked retraining job.

---

## 5. How to Train and Evaluate

```powershell
# 1. Clean, validate, and deduplicate all incoming/training data
python training/prepare_data.py

# 2. Train candidate model, check acceptance gates, and deploy atomically
python training/train.py

# 3. Run honest comparative evaluation on strictly held-out test splits
python training/evaluate.py

# 4. (Optional) Run background file watcher with debounced auto-retraining
python training/watch.py
```

---

## 6. How to Test

Run the full automated test suite (81 tests across all components and hardening phases):
```powershell
pytest -v
```
## 7. Runtime ML integration contract

The ML package exposes `pipeline.enrich_event()` as the single orchestration entry point for the AI/ML stage. It is intended to be called **after Spark has performed validation, streaming deduplication, and windowed aggregation**.

```text
Kafka
  ↓
Spark Structured Streaming
  ↓
Validation / cleaning
  ↓
Event-ID deduplication
  ↓
Windowed aggregation
  ↓
ml.pipeline.enrich_event()
  ├─ Classification
  ├─ Duplicate evidence against recent events
  ├─ Credibility scoring + corroboration
  ├─ Spatial-temporal cluster assignment
  └─ Explainability
  ↓
weather.events
  ↓
PostgreSQL / PostGIS
```

`enrich_event()` returns a stable `ai` object containing classification, duplicate evidence, credibility factors/reasons, cluster ID (when available), and explanations, while preserving top-level compatibility fields for existing consumers.

### Package usage

```python
from ml.pipeline import enrich_event

result = enrich_event(
    event,
    recent_events=recent_events,
    active_clusters=active_clusters,
)
```

The package can also still be imported in the existing Spark-worker style where `ml/` is placed on `PYTHONPATH`; package-relative imports now support both modes.
