# 05 — AI / ML Specification

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `05_AI_ML_SPEC.md`
**Version:** 1.2
**Status:** AWAITING APPROVAL
**Derived from:** `01_ARCHITECTURE.md` v1.3 + `02_DATA_SCHEMA.md` v1.1 + `03_KAFKA_CONTRACT.md` v1.0 + `04_API_CONTRACT.md` v1.0
**Last updated:** 2026-09-02

---

## Change Control

No ML function signature, scoring methodology, threshold value, taxonomy rule,
clustering parameter, or Spark integration pattern may be changed without
updating this document first and obtaining architect sign-off.

---

## 1. Document Metadata

This document is the **single source of truth for all AI/ML functionality** in the
platform. It defines every ML module, its inputs, outputs, algorithm, configuration,
integration with Spark, and testing strategy.

**Scope:** MVP hackathon (5-day sprint).
**Approach:** Lightweight hybrid — rule-based classification (with trained-model upgrade path), weighted scoring,
similarity-based deduplication, spatial-temporal clustering, template-based explainability.

**Training architecture (three distinct stages):**

1. **External experimentation** — Jupyter notebooks or Google Colab used to explore algorithms,
   features, preprocessing, and model selection. This is research, not deployment.
2. **Project-owned offline training** — Reproducible training scripts in the repository
   (`training/`) that produce the final model artifact. Run manually or via CI. Never runs at runtime.
3. **Runtime inference** — The deployed application loads the pre-trained model artifact and performs
   predictions. The runtime NEVER trains a model.

```text
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
                   Model Artifact (.joblib)
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

**Migration strategy:** Rule-based classification on Day 1–2; trained model (TF-IDF + Logistic
Regression) as drop-in replacement once validated. The Spark pipeline never knows which backend
is active — it always calls `classify_event()`.

---

## 2. ML Architecture

### 2.1 Integration Pattern

```
Kafka (weather.raw / citizen.raw / social.raw / government.raw)
  ↓
Spark Structured Streaming (validates, cleans, normalises)
  ↓
ML Python Library (local import, NOT a separate service)
  ├── classifier   → classify_event()
  ├── credibility  → score_credibility()
  ├── dedup        → compute_duplicate_score()
  ├── clustering   → assign_cluster()
  └── explainability → generate_reasons()
  ↓
Kafka: weather.events (ai.* fully populated)
```

### 2.2 Deployment Model

| Property | Value |
|----------|-------|
| Location | `services/ml/` |
| Packaging | Python library; `COPY`-ed into Spark Docker image at build time |
| Docker service | **None** — no separate container, no HTTP port |
| Import path | `from ml.classifier.event_classifier import classify_event` etc. |
| Runtime | Inside Spark worker process (same JVM via PySpark) |
| Dependencies (rule-based) | `numpy`, `pyyaml` only |
| Dependencies (trained model) | `numpy`, `pyyaml`, `scikit-learn`, `joblib` |
| Classifier backend | Configurable via `CLASSIFIER_BACKEND` env var (default: `rule_based`) |

> **Critical:** ML is a **library dependency** of Spark, not a standalone service.
> There is no ML HTTP API, no model-serving infrastructure, no GPU requirement.
>
> **Classifier abstraction:** The Spark pipeline calls `classify_event()` which
> delegates to either `RuleBasedClassifier` or `TrainedModelClassifier` depending
> on `CLASSIFIER_BACKEND`. The pipeline code does not change when switching backends.

### 2.3 Function Signatures (Architecture §6.1)

| Function | Execution Context | Spark Pattern | Window Required? |
|----------|------------------|---------------|-----------------|
| `classify_event(description, category_hint)` | Per-record | Pandas UDF (scalar) | No |
| `score_credibility(event_dict)` | Per-record | Pandas UDF (scalar) | No |
| `generate_reasons(event_dict, factors)` | Per-record | Pandas UDF (scalar) | No |
| `compute_duplicate_score(event_dict, recent_events)` | Per-micro-batch | `foreachBatch` handler | **Yes** — needs recent events list |
| `assign_cluster(event_dict, active_clusters)` | Per-micro-batch | `foreachBatch` handler | **Yes** — needs active clusters state |

> Functions that require window state **cannot** be Pandas UDFs.
> They run inside `foreachBatch` with `batch_df.collect()` (safe for MVP micro-batch sizes).

---

## 3. MVP ML Components

| Component | MVP Method | Input | Output | Model Training Required? |
|-----------|-----------|-------|--------|--------------------------|
| Classification | Rule-based + keyword NLP | `event.description` + `event.category` hint | `ai.classified_category`, `ai.classification_confidence` | **No** |
| Credibility | Weighted multi-factor scoring | Source trust, corroboration, metadata | `ai.credibility_score`, `ai.credibility_reasons` | **No** |
| Duplicate detection | Fuzzy/similarity matching | Current event + recent events window | `ai.duplicate_score` | **No** |
| Clustering | Spatial-temporal grouping | Event location, time, category | `ai.cluster_id` | **No** |
| Explainability | Deterministic templates | All ML outputs + input evidence | `ai.credibility_reasons` | **No** |

**Stage 1 (Day 1–2):** No model training required. Classification uses deterministic rule-based logic with configurable thresholds.

**Stage 2 (Day 3–5, optional):** If time permits, train a supervised classifier (TF-IDF + Logistic Regression) as a drop-in replacement for the rule-based classifier. The trained model must exceed the rule-based baseline on validation F1 before activation. See §4.6–§4.10 for the full migration plan.

---

## 4. Event Classification

### 4.1 Allowed Categories

The ML classifier MUST output one of these exact values (from `02_DATA_SCHEMA.md §1.2`):

```
rainfall          heavy_rainfall       flood
thunderstorm      lightning            heatwave
fog               dust_storm           strong_wind
hailstorm         cyclone              other
```

**No additional categories may be added** without architect approval and schema change.

### 4.2 Classification Inputs

| Input | Field | Usage |
|-------|-------|-------|
| Description text | `event.description` | Primary signal — keyword/phrase matching |
| Category hint | `event.category` | Source adapter's initial classification; used as a tiebreaker |
| Source type | `source_type` | Weather API sources have structured data; social/citizen rely on text |
| Severity hint | `event.severity` | May indicate event intensity |
| Hashtags | `social_metadata.hashtags` | Supplementary keyword signal for social sources |

### 4.3 Deterministic Logic

The classifier uses keyword dictionaries and pattern matching — no probabilistic model.

**Classification algorithm:**

```
1. Normalize text (lowercase, strip punctuation, Unicode normalization)
2. For each category in priority order (§6):
   a. Match against category keyword dictionary (§4.4)
   b. Count matching keywords/phrases
   c. Compute category score (0.0–1.0)
3. Select category with highest score
4. If source adapter provided a category hint and it matches the top result → boost confidence
5. If no keywords match → fall back to source adapter category hint, or "other"
6. Compute confidence (§7)
```

### 4.4 Keyword Dictionaries

Keywords are defined in `services/ml/classifier/rules.py` as configuration,
NOT hardcoded business logic.

#### English Keywords (Primary)

| Category | Keywords / Phrases |
|----------|-------------------|
| `flood` | flood, flooded, flooding, waterlogging, waterlogged, inundated, submerged, overflow, flash flood, rising water, submerged roads, knee-deep water |
| `heavy_rainfall` | heavy rain, very heavy rainfall, torrential rain, extremely heavy rain, intense rainfall, record rainfall |
| `rainfall` | rain, rainfall, raining, showers, drizzle, precipitation, light rain |
| `thunderstorm` | thunderstorm, thunder, storm, lightning storm, electrical storm |
| `lightning` | lightning, lightning strike, lightning bolt, thunderbolt |
| `heatwave` | heatwave, heat wave, extreme heat, scorching,高温,高温预警, heat warning, very hot, temperature above 40, temperature above 42, sweltering |
| `fog` | fog, foggy, misty, low visibility, dense fog, smog, haze |
| `dust_storm` | dust storm, sandstorm, dust, sandy winds, dust devil |
| `strong_wind` | strong wind, gale, gusty winds, high winds, wind speed, cyclonic winds, windy |
| `hailstorm` | hail, hailstones, hailstorm, ice pellets, hail damage |
| `cyclone` | cyclone, cyclonic, typhoon, tropical storm, tropical depression, very severe cyclonic storm |

#### Hindi Keywords (Supplementary)

| Category | Keywords |
|----------|---------|
| `flood` | बाढ़, पानी भरा, जलभराव, डूबा हुआ |
| `heavy_rainfall` | भारी बारिश, मूसलाधार बारिश |
| `rainfall` | बारिश, वर्षा, बूँदाबांदी |
| `heatwave` | लू, गर्मी की लहर, अत्यधिक गर्मी |
| `thunderstorm` | तूफान, बिजली गिरना, आंधी |
| `cyclone` | चक्रवात |
| `hailstorm` | ओलावृष्टि, ओले |
| `fog` | कोहरा, धुंध |

#### Marathi Keywords (Supplementary)

| Category | Keywords |
|----------|---------|
| `flood` | पूर, पाण्याचा प्रवाह, जलभराव |
| `heavy_rainfall` | मुसळधार पाऊस, जड पाऊस |
| `rainfall` | पाऊस, सरी |
| `heatwave` | उन्हाची लाट, अत्यधिक उकड |
| `thunderstorm` | वादळ, मेघगर्जन |
| `hailstorm` | गाठणे, अंबरी |
| `fog` | धुके |

> **Note:** If the master specification requires broader multilingual support
> beyond English/Hindi/Marathi, the keyword dictionaries in `rules.py` can be
> extended without code changes — they are configuration data, not logic.

### 4.5 Category Compatibility Map

Used by deduplication and clustering to determine if two categories describe the
same type of event:

```
Compatible pairs:
  (rainfall, heavy_rainfall)
  (flood, heavy_rainfall)
  (flood, rainfall)
  (thunderstorm, lightning)
  (thunderstorm, strong_wind)
  (cyclone, heavy_rainfall)
  (cyclone, strong_wind)
  (hailstorm, thunderstorm)
  (hailstorm, heavy_rainfall)
```

Two events with compatible categories can be clustered together if they also
match on location and time.

### 4.6 Classifier Interface (Abstraction Layer)

> **Critical design principle:** The Spark pipeline must NOT know whether
> classification is rule-based or model-based. Both implementations expose the
> same function signature and return the same output structure.

**Public interface:**

```python
# services/ml/classifier/interface.py

class BaseClassifier(ABC):
    """Abstract classifier interface."""

    @abstractmethod
    def predict(self, description: str, category_hint: str | None) -> dict:
        """
        Classify a weather event.

        Args:
            description: Event description text.
            category_hint: Source adapter's initial category (optional).

        Returns:
            {
                "classified_category": str,      # One of §4.1 enum values
                "classification_confidence": float  # 0.0–1.0
            }
        """
        ...

    @abstractmethod
    def explain(self, description: str, category_hint: str | None) -> list[str]:
        """Return human-readable reasons for the classification."""
        ...
```

**Public function (called by Spark):**

```python
# services/ml/classifier/event_classifier.py

def classify_event(description: str, category_hint: str | None = None) -> dict:
    """Classify a weather event. Delegates to active backend."""
    return _get_classifier().predict(description, category_hint)
```

**Backend selection:**

```python
import os

def _get_classifier() -> BaseClassifier:
    backend = os.environ.get("CLASSIFIER_BACKEND", "rule_based")
    if backend == "rule_based":
        from ml.classifier.rule_based_classifier import RuleBasedClassifier
        return RuleBasedClassifier()
    elif backend == "trained":
        from ml.classifier.trained_classifier import TrainedModelClassifier
        return TrainedModelClassifier()
    elif backend == "hybrid":
        from ml.classifier.hybrid_classifier import HybridClassifier
        return HybridClassifier()
    else:
        raise ValueError(f"Unknown CLASSIFIER_BACKEND: {backend}")
```

**Spark code never changes:**

```python
# In Spark pipeline — this line stays the same regardless of backend
result = classify_event(description, category_hint)
```

### 4.7 Rule-Based Classifier (Stage 1)

**File:** `services/ml/classifier/rule_based_classifier.py`

Implements `BaseClassifier` using keyword dictionaries from §4.4.

```python
class RuleBasedClassifier(BaseClassifier):
    """Deterministic keyword-based classifier."""

    def predict(self, description: str, category_hint: str | None = None) -> dict:
        normalized = normalize_text(description)
        scores = {cat: score_category(normalized, cat) for cat in VALID_CATEGORIES}
        category, score = resolve_category(scores, category_hint)
        confidence = compute_confidence(score, ...)
        return {
            "classified_category": category,
            "classification_confidence": confidence,
        }

    def explain(self, description: str, category_hint: str | None = None) -> list[str]:
        normalized = normalize_text(description)
        matched = find_matched_keywords(normalized)
        if matched:
            return [f"Matched keywords: {', '.join(matched)}"]
        return ["No keyword matches; using source adapter hint"]
```

**Confidence generation (rule-based):**

| Signal | Confidence contribution |
|--------|----------------------|
| Strong keyword match (≥3 hits) | 0.80–0.95 |
| Moderate match (1–2 hits) | 0.50–0.79 |
| Weak match (phrase partial) | 0.30–0.49 |
| Category hint only (no keywords) | 0.20–0.30 |
| No match, no hint | 0.10 |

### 4.8 Trained Model Classifier (Stage 2)

**File:** `services/ml/classifier/trained_classifier.py`

**When to implement:** Only after rule-based classifier is fully working and a
labelled training dataset is available.

**Recommended model:**

```
TF-IDF Vectorizer + Logistic Regression
```

Saved as a single sklearn Pipeline via `joblib`:

```python
# Training script (services/ml/training/train_classifier.py)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2))),
    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
])

pipeline.fit(X_train, y_train)
joblib.dump(pipeline, "models/event_classifier/model.pkl")
```

**Inference:**

```python
class TrainedModelClassifier(BaseClassifier):
    """ML model-based classifier."""

    def __init__(self):
        model_path = os.environ.get("MODEL_PATH", "/opt/models/event_classifier/model.pkl")
        self._model = joblib.load(model_path)

    def predict(self, description: str, category_hint: str | None = None) -> dict:
        prediction = self._model.predict([description])[0]
        probabilities = self._model.predict_proba([description])[0]
        confidence = float(max(probabilities))
        return {
            "classified_category": prediction,
            "classification_confidence": round(confidence, 3),
        }

    def explain(self, description: str, category_hint: str | None = None) -> list[str]:
        prediction, confidence = self.predict(description, category_hint)
        return [f"Model confidence {confidence:.2f} for {prediction} based on learned text features"]
```

### 4.9 Hybrid Classifier (Optional Fallback)

**File:** `services/ml/classifier/hybrid_classifier.py`

Uses the trained model when confidence is high; falls back to rules otherwise.

```env
CLASSIFIER_BACKEND=hybrid
MODEL_CONFIDENCE_THRESHOLD=0.75
```

```python
class HybridClassifier(BaseClassifier):
    def __init__(self):
        self._model = TrainedModelClassifier()
        self._rules = RuleBasedClassifier()
        self._threshold = float(os.environ.get("MODEL_CONFIDENCE_THRESHOLD", "0.75"))

    def predict(self, description: str, category_hint: str | None = None) -> dict:
        model_result = self._model.predict(description, category_hint)
        if model_result["classification_confidence"] >= self._threshold:
            return model_result
        return self._rules.predict(description, category_hint)
```

> **MVP recommendation:** Start with `rule_based` only. Add `trained` or `hybrid`
> only if a trained model is validated and time permits.

### 4.10 Training Pipeline (Separate from Runtime)

> **Training MUST NOT happen inside Spark Structured Streaming.**
> See §19 for the definitive three-stage training architecture.

**Offline training pipeline** (runs outside Docker, manually or via CI):

```
training/prepare_data.py
        ↓
Labelled Dataset (CSV)
        ↓
training/train.py
        ↓
Text Cleaning + TF-IDF Vectorization + Logistic Regression
        ↓
training/evaluate.py
        ↓
Validation (F1, Precision, Recall, Confusion Matrix)
        ↓
Save sklearn Pipeline (joblib)
        ↓
models/event_classifier/model.pkl
```

**Training data format:**

```csv
text,category
"Heavy rain in Mumbai",heavy_rainfall
"Roads flooded in Kurla",flood
"Thunder and lightning reported",thunderstorm
"Extreme heat in Nagpur",heatwave
"Strong winds damaged trees",strong_wind
```

**Data sources for labelling:**
1. Existing historical weather/event data
2. Government/public datasets
3. RSS/news data (extracted text with category labels)
4. Carefully labelled synthetic data
5. Manually labelled examples

**Evaluation criteria for switching:**

| Metric | Rule-Based Baseline | Trained Model Target |
|--------|--------------------|--------------------|
| Overall F1 | Measured | > Rule-based F1 |
| Per-category F1 | Measured | > 0.80 for all demo categories |
| Inference latency | < 5 ms | < 50 ms (acceptable for Spark) |

> **Decision rule:** Switch to trained model only if it exceeds the rule-based
> baseline on **overall F1** AND does not have any critical category below 0.60 F1.

**Model artifact location:**

```
models/event_classifier/
├── model.pkl                       # The trained sklearn Pipeline (joblib)
└── metadata.json                   # Model version, training date, metrics
```

At runtime, the Spark worker loads from `MODEL_PATH` (default: `/opt/models/event_classifier/model.pkl`).

**Metadata example:**

```json
{
  "model_version": "v1",
  "trained_at": "2026-09-03",
  "algorithm": "logistic_regression",
  "features": "tfidf_10000_bigrams",
  "validation_f1": 0.91,
  "training_samples": 5000,
  "categories": 12
}
```

**Runtime dependency change when using trained model:**

| Dependency | Rule-Based | Trained Model |
|------------|-----------|---------------|
| `numpy` | Yes | Yes |
| `pyyaml` | Yes | Yes |
| `scikit-learn` | **No** | **Yes** |
| `joblib` | **No** | **Yes** |

**Docker deployment change:**

```yaml
# docker-compose.yml — Spark worker
volumes:
  - ./services/ml:/opt/ml
  - ./models:/opt/models    # Model artifact mount
```

```env
# .env
CLASSIFIER_BACKEND=rule_based           # Change to 'trained' after validation
MODEL_PATH=/opt/models/event_classifier/model.pkl
```

> **What does NOT change when switching classifiers:** Source adapters, Canonical
> Event schema, Kafka topics, Kafka envelope, Spark pipeline architecture,
> PostgreSQL schema, FastAPI endpoints, React frontend, Docker service topology.

---

## 5. Classification Pipeline

```
Event description + source metadata + category hint
        ↓
   Text Normalization
   (lowercase, strip punctuation, Unicode NFKD normalize)
        ↓
   Keyword/Phrase Matching
   (match against §4.4 dictionaries; count hits per category)
        ↓
   Category Scoring
   (hits → score; exact phrase matches score higher than single keywords)
        ↓
   Priority/Conflict Resolution
   (§6 — deterministic priority order)
        ↓
   Confidence Calculation
   (§7 — based on evidence strength)
        ↓
   Output:
   ai.classified_category  (enum from §4.1)
   ai.classification_confidence  (float 0.0–1.0)
```

### 5.1 Text Normalization

```python
def normalize_text(text: str) -> str:
    """Normalize description text for keyword matching."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)       # Unicode normalization
    text = re.sub(r"[^\w\s]", " ", text)             # Remove punctuation
    text = re.sub(r"\s+", " ", text).strip()         # Collapse whitespace
    return text
```

### 5.2 Keyword Scoring

```python
def score_category(normalized_text: str, category: str) -> float:
    """Score how well text matches a category's keywords."""
    keywords = KEYWORD_DICT[category]                  # From rules.py config
    exact_phrase_hits = sum(1 for phrase in keywords["phrases"] if phrase in normalized_text)
    single_keyword_hits = sum(1 for kw in keywords["single"] if kw in normalized_text)

    # Phrases are weighted more than single keywords
    raw_score = (exact_phrase_hits * 3) + (single_keyword_hits * 1)
    max_possible = (len(keywords["phrases"]) * 3) + (len(keywords["single"]) * 1)

    if max_possible == 0:
        return 0.0
    return min(raw_score / max_possible, 1.0)
```

---

## 6. Category Priority Rules

When multiple categories receive non-zero scores, the **highest-priority category
wins**. This is deterministic and unambiguous.

### 6.1 Priority Order (highest → lowest)

```
1.  cyclone
2.  flood
3.  heavy_rainfall
4.  hailstorm
5.  thunderstorm
6.  lightning
7.  heatwave
8.  strong_wind
9.  dust_storm
10. fog
11. rainfall
12. other
```

### 6.2 Resolution Logic

```python
def resolve_category(scores: dict[str, float], category_hint: str | None) -> tuple[str, float]:
    """Select the winning category using priority rules."""
    # Filter to categories with score > 0
    candidates = {cat: score for cat, score in scores.items() if score > 0.0}

    if not candidates:
        # No keyword matches — fall back to source adapter hint
        if category_hint and category_hint in VALID_CATEGORIES:
            return category_hint, 0.30  # Low confidence for hint-only classification
        return "other", 0.20

    # Sort by (score DESC, priority ASC) — higher score wins; ties broken by priority
    ranked = sorted(
        candidates.items(),
        key=lambda x: (-x[1], CATEGORY_PRIORITY.index(x[0]))
    )
    winner = ranked[0]
    return winner[0], winner[1]
```

### 6.3 Example Resolution

Input text: *"Heavy rain caused flooding in Mumbai"*

| Category | Score |
|----------|-------|
| `heavy_rainfall` | 0.72 |
| `flood` | 0.65 |
| `rainfall` | 0.30 |

Result: `heavy_rainfall` wins (higher score: 0.72 > 0.65).

If scores were tied (both 0.65): `flood` wins (priority 2 < priority 3).

---

## 7. Classification Confidence

### 7.1 Confidence Formula

```python
def compute_confidence(
    winner_score: float,
    runner_up_score: float,
    keyword_hit_count: int,
    source_has_structured_data: bool,
    category_hint_matches: bool
) -> float:
    """Compute classification confidence (0.0–1.0)."""
    base = winner_score * 0.50                          # Primary: how strong the match is
    separation = (winner_score - runner_up_score) * 0.25  # Gap between #1 and #2
    evidence = min(keyword_hit_count / 5.0, 1.0) * 0.15  # More keywords = more evidence
    structured = 0.05 if source_has_structured_data else 0.0
    hint_match = 0.05 if category_hint_matches else 0.0

    raw = base + separation + evidence + structured + hint_match
    return round(min(max(raw, 0.0), 1.0), 3)
```

### 7.2 Confidence Thresholds (Configurable)

| Range | Label | Display Behaviour |
|-------|-------|------------------|
| ≥ 0.80 | High confidence | Category badge with strong colour |
| 0.60–0.79 | Medium confidence | Category badge with standard colour |
| 0.40–0.59 | Low confidence | Category badge with muted colour |
| < 0.40 | Very low confidence | Category shown but flagged as uncertain |

> These thresholds are configurable via `config/ml_config.yaml` (or environment
> variables). The values above are starting defaults.

### 7.3 Storage

| Field | Value |
|-------|-------|
| `ai.classified_category` | Winning category enum string |
| `ai.classification_confidence` | Float, 3 decimal places |

---

## 8. Credibility Scoring

### 8.1 Multi-Factor Weighted Score

```python
def score_credibility(event: dict) -> tuple[float, list[str]]:
    """Compute credibility score (0.0–1.0) and human-readable reasons."""
    factors = {}

    factors["source_trust"] = compute_source_trust(event)           # Weight: 0.30
    factors["corroboration"] = compute_corroboration(event)         # Weight: 0.25
    factors["weather_agreement"] = compute_weather_agreement(event) # Weight: 0.20
    factors["temporal_consistency"] = compute_temporal(event)       # Weight: 0.10
    factors["spatial_consistency"] = compute_spatial(event)         # Weight: 0.10
    factors["content_quality"] = compute_content_quality(event)     # Weight: 0.05

    score = sum(factors[k] * CREDIBILITY_WEIGHTS[k] for k in factors)
    score = round(min(max(score, 0.0), 1.0), 3)

    reasons = generate_credibility_reasons(factors, event)
    return score, reasons
```

### 8.2 Factor Weights (Configurable)

| Factor | Weight | Rationale |
|--------|-------:|-----------|
| Source trust | 0.30 | Pre-computed reputation of the source type |
| Independent corroboration | 0.25 | Multiple independent reports of the same event |
| Weather/API agreement | 0.20 | Whether structured weather data confirms the event |
| Temporal consistency | 0.10 | Report timestamp is within expected window |
| Spatial consistency | 0.10 | Coordinates align with stated location |
| Content quality | 0.05 | Description length, specificity, absence of spam markers |

### 8.3 Factor Implementations

#### Source Trust (0.30 weight)

```python
def compute_source_trust(event: dict) -> float:
    """Return source trust score from configuration."""
    source_type = event.get("source_type", "")
    return SOURCE_TRUST_CONFIG.get(source_type, 0.50)
```

See §9 for default source trust values.

#### Independent Corroboration (0.25 weight)

```python
def compute_corroboration(event: dict) -> float:
    """Score based on number of independent corroborating reports."""
    corroborations = count_corroborations(event)  # See §10
    if corroborations == 0:
        return 0.0
    elif corroborations == 1:
        return 0.40
    elif corroborations == 2:
        return 0.70
    elif corroborations == 3:
        return 0.85
    else:
        return min(0.95, 0.85 + (corroborations - 3) * 0.03)
```

#### Weather/API Agreement (0.20 weight)

```python
def compute_weather_agreement(event: dict) -> float:
    """Check if structured weather data agrees with the reported event."""
    # If source_type is "weather_api", the event IS the weather data → full agreement
    if event.get("source_type") == "weather_api":
        return 1.0

    # For other sources, check if a recent weather_api event exists
    # in the same location with compatible conditions
    # (queried from the in-memory recent events window)
    # This is a simplified check — not a full meteorological analysis
    recent_api_events = find_nearby_weather_api_events(event)
    if not recent_api_events:
        return 0.30  # No weather data to compare; neutral score

    # Check if any API event has a compatible category
    compatible = any(
        categories_are_compatible(event.get("event", {}).get("category"), api_evt.get("event", {}).get("category"))
        for api_evt in recent_api_events
    )
    return 0.90 if compatible else 0.20
```

> **Important:** If no weather API data is available for comparison, the score
> is neutral (0.30). The credibility reasons must NOT claim weather confirmation
> when none exists.

#### Temporal Consistency (0.10 weight)

```python
def compute_temporal(event: dict) -> float:
    """Check if event timestamp is reasonable."""
    event_ts = parse_timestamp(event.get("timestamp"))
    ingestion_ts = parse_timestamp(event.get("ingestion_timestamp"))
    if not event_ts or not ingestion_ts:
        return 0.50  # Cannot evaluate

    lag_minutes = (ingestion_ts - event_ts).total_seconds() / 60.0
    if lag_minutes < 0:
        return 0.20  # Event in the future — suspicious
    elif lag_minutes < 30:
        return 1.0   # Very recent — good
    elif lag_minutes < 120:
        return 0.70  # Within 2 hours
    elif lag_minutes < 360:
        return 0.50  # Within 6 hours
    else:
        return 0.30  # Stale report
```

#### Spatial Consistency (0.10 weight)

```python
def compute_spatial(event: dict) -> float:
    """Check if coordinates are consistent with stated city."""
    location = event.get("location", {})
    lat, lon = location.get("latitude"), location.get("longitude")
    city = location.get("city")

    if lat is None or lon is None:
        return 0.50  # No coordinates to evaluate
    if city is None:
        return 0.70  # Has coordinates but no city name — acceptable

    # Check if coordinates fall within expected bounding box for the city
    # (loaded from config/india_cities.json at startup)
    expected_box = CITY_BOUNDING_BOXES.get(city)
    if expected_box is None:
        return 0.60  # City not in lookup table — neutral

    if (expected_box["min_lat"] <= lat <= expected_box["max_lat"] and
        expected_box["min_lon"] <= lon <= expected_box["max_lon"]):
        return 1.0
    else:
        return 0.30  # Coordinates don't match city
```

#### Content Quality (0.05 weight)

```python
def compute_content_quality(event: dict) -> float:
    """Assess description quality."""
    description = event.get("event", {}).get("description") or ""
    length = len(description.strip())

    if length == 0:
        return 0.20  # No description
    elif length < 20:
        return 0.40  # Very short
    elif length < 100:
        return 0.70  # Moderate
    else:
        return 0.90  # Substantial description
```

### 8.4 Example Calculation

```
Event: Citizen report about Mumbai flooding

Source trust:      0.60  × 0.30 = 0.180
Corroboration:     0.85  × 0.25 = 0.213  (3 independent reports)
Weather agreement: 0.90  × 0.20 = 0.180  (API confirms heavy rain)
Temporal:          1.00  × 0.10 = 0.100  (reported within 10 minutes)
Spatial:           1.00  × 0.10 = 0.100  (coordinates match Mumbai)
Content quality:   0.90  × 0.05 = 0.045  (detailed description)
─────────────────────────────────────────
Final credibility:                  0.818
```

---

## 9. Source Trust Configuration

Source trust values are loaded from configuration at Spark startup.
They represent **initial assumptions**, NOT measured historical accuracy.

### 9.1 Default Values (Configurable)

| `source_type` | Default Trust Score | Rationale |
|---------------|--------------------:|-----------|
| `government_dataset` | 0.95 | Official government data; high assumed accuracy |
| `weather_api` | 0.95 | Structured API data from established provider (Open-Meteo) |
| `website` | 0.80 | Allowlisted news/information sites |
| `rss` | 0.75 | Public RSS feeds; content varies |
| `citizen` | 0.60 | Well-intentioned but unverified; may have reporting errors |
| `social` | 0.55 | API-compliant social media; mixed reliability |
| `simulated_social` | 0.40 | Clearly labelled simulation; not genuine data |
| `synthetic` | 0.50 | Test data; not presented as real |

### 9.2 Configuration File

```yaml
# services/ml/config/source_trust.yaml
source_trust:
  government_dataset: 0.95
  weather_api: 0.95
  website: 0.80
  rss: 0.75
  citizen: 0.60
  social: 0.55
  simulated_social: 0.40
  synthetic: 0.50
```

> These values are **starting assumptions**. If the `sources` table has a
> `trust_score` override for a specific `source_name`, that value takes
> precedence over the source_type default.

---

## 10. Corroboration Detection

### 10.1 Definition

Two reports are considered **corroborating** when they describe the same
real-world event and come from sufficiently independent sources.

### 10.2 Independence Criteria

A report qualifies as a **separate independent report** when ALL of:

1. **Different `source_id`** — not a duplicate of the same source record
2. **Different `source_name`** — not from the exact same publication/feed
   (exception: same `source_name` is allowed if `source_id` differs and
   temporal gap > 5 minutes)
3. **Compatible `event.category`** — categories must be semantically compatible
   (e.g., `heavy_rainfall` and `flood` are compatible; `heatwave` and `flood` are not)
4. **Spatial proximity** — within `CORROBORATION_RADIUS_KM` (default: 10 km)
5. **Temporal proximity** — within `CORROBORATION_WINDOW_MINUTES` (default: 30 minutes)

### 10.3 Category Compatibility Map

```python
CATEGORY_COMPATIBILITY = {
    "rainfall":        {"rainfall", "heavy_rainfall", "flood"},
    "heavy_rainfall":  {"rainfall", "heavy_rainfall", "flood", "thunderstorm"},
    "flood":           {"rainfall", "heavy_rainfall", "flood"},
    "thunderstorm":    {"thunderstorm", "lightning", "heavy_rainfall"},
    "lightning":       {"thunderstorm", "lightning"},
    "heatwave":        {"heatwave"},
    "fog":             {"fog"},
    "dust_storm":      {"dust_storm", "strong_wind"},
    "strong_wind":     {"strong_wind", "cyclone", "dust_storm"},
    "hailstorm":       {"hailstorm", "thunderstorm"},
    "cyclone":         {"cyclone", "strong_wind", "heavy_rainfall", "flood"},
    "other":           set(),  # "other" does not corroborate anything
}
```

### 10.4 Deduplication of Sources

Before counting corroboration, apply source deduplication:

- If two events share the same `source_id` → count as **1 report** (not 2)
- If two events share the same `source_url` → count as **1 report** (not 2)
- If two events have the same `author_id` AND are within 5 minutes → count as **1 report**

This prevents the same article reposted across feeds from inflating corroboration.

---

## 11. Duplicate Detection

### 11.1 Score Definition

`ai.duplicate_score` ranges from 0.0 to 1.0:

```
0.0 = unlikely duplicate (distinct event)
1.0 = almost certainly duplicate (same event reported again)
```

### 11.2 Similarity Features

The duplicate detector computes a composite score from weighted features:

| Feature | Weight | Description |
|---------|-------:|-------------|
| Text similarity | 0.30 | Normalized description overlap (Jaccard similarity on keywords) |
| Source ID match | 0.20 | Same `source_id` → 1.0; different → 0.0 |
| Source URL match | 0.15 | Same `source_url` → 1.0; different → 0.0 |
| Category match | 0.15 | Same category → 1.0; compatible → 0.5; different → 0.0 |
| Time difference | 0.10 | Score based on minutes apart (closer = higher) |
| Geographic distance | 0.10 | Score based on km apart (closer = higher) |

### 11.3 Text Similarity (Jaccard on Keywords)

```python
def text_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity on normalized keyword sets."""
    words_a = set(normalize_text(text_a).split())
    words_b = set(normalize_text(text_b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
```

### 11.4 Time Difference Score

```python
def time_difference_score(minutes_diff: float) -> float:
    """Score based on time difference between events."""
    if minutes_diff <= 5:
        return 1.0
    elif minutes_diff <= 30:
        return 0.8
    elif minutes_diff <= 60:
        return 0.5
    elif minutes_diff <= 180:
        return 0.2
    else:
        return 0.0
```

### 11.5 Geographic Distance Score

```python
def geographic_distance_score(distance_km: float) -> float:
    """Score based on distance between events."""
    if distance_km <= 0.5:
        return 1.0
    elif distance_km <= 2.0:
        return 0.8
    elif distance_km <= 5.0:
        return 0.5
    elif distance_km <= 10.0:
        return 0.2
    else:
        return 0.0
```

### 11.6 Composite Score

```python
def compute_duplicate_score(current: dict, recent_events: list[dict]) -> float:
    """Compute duplicate score against all recent events."""
    if not recent_events:
        return 0.0  # No recent events to compare — cannot be duplicate

    scores = []
    for recent in recent_events:
        score = (
            DUP_WEIGHTS["text"]     * text_similarity(current["description"], recent["description"]) +
            DUP_WEIGHTS["source_id"] * (1.0 if current["source_id"] == recent["source_id"] else 0.0) +
            DUP_WEIGHTS["source_url"] * (1.0 if current.get("source_url") == recent.get("source_url") and current.get("source_url") else 0.0) +
            DUP_WEIGHTS["category"] * category_match_score(current["category"], recent["category"]) +
            DUP_WEIGHTS["time"]     * time_difference_score(time_diff_minutes(current, recent)) +
            DUP_WEIGHTS["distance"] * geographic_distance_score(haversine_km(current, recent))
        )
        scores.append(score)

    return round(max(scores), 3)  # Return the highest duplicate score
```

---

## 12. Duplicate Thresholds

### 12.1 Threshold Values (Configurable)

| Score Range | Label | System Behaviour |
|-------------|-------|-----------------|
| ≥ 0.85 | Probable duplicate | `ai.duplicate_score` set; flagged for admin review |
| 0.60–0.84 | Possible duplicate | `ai.duplicate_score` set; displayed normally |
| < 0.60 | Likely distinct | `ai.duplicate_score` set; no special handling |

### 12.2 Important Rules

- **No automatic deletion.** All records are retained in the database.
- Duplicates are **flagged, not removed**. Admin can manually mark via `POST /verification` with `action: "marked_duplicate"`.
- The `verification.status` may be set to `"duplicate"` by admin action only, NOT automatically by ML.
- ML sets `ai.duplicate_score` only — it does NOT change `verification.status`.

---

## 13. Event Clustering

### 13.1 Purpose

Clustering groups reports about the **same real-world event or event episode**
into a single cluster. A cluster represents one incident (e.g., "the Mumbai
flooding of 31 Aug 2026"), not individual reports.

### 13.2 Clustering Criteria

An event is assigned to an existing cluster when ALL of:

1. **Category compatible** — same or semantically compatible category (§10.3)
2. **Spatial proximity** — within `CLUSTER_RADIUS_KM` of the cluster centroid
3. **Temporal proximity** — within `CLUSTER_TIME_WINDOW_MINUTES` of the cluster's latest event

### 13.3 Default Parameters (Configurable)

| Parameter | Default | Description |
|-----------|--------:|-------------|
| `CLUSTER_RADIUS_KM` | 3.0 | Maximum distance from cluster centroid |
| `CLUSTER_TIME_WINDOW_MINUTES` | 30 | Maximum time gap from cluster's latest event |
| `CLUSTER_MAX_SIZE` | 50 | Maximum events per cluster (prevents runaway clusters) |

### 13.4 Clustering Algorithm

```python
def assign_cluster(event: dict, active_clusters: list[dict]) -> str | None:
    """Assign event to an existing cluster or create a new one."""
    best_cluster = None
    best_score = 0.0

    for cluster in active_clusters:
        # Check category compatibility
        if not categories_are_compatible(event["category"], cluster["category"]):
            continue

        # Check spatial proximity
        distance = haversine_km(
            event["latitude"], event["longitude"],
            cluster["centroid_lat"], cluster["centroid_lon"]
        )
        if distance > CLUSTER_RADIUS_KM:
            continue

        # Check temporal proximity
        time_gap = abs((event["timestamp"] - cluster["last_event_at"]).total_seconds() / 60)
        if time_gap > CLUSTER_TIME_WINDOW_MINUTES:
            continue

        # Check cluster size
        if cluster["member_count"] >= CLUSTER_MAX_SIZE:
            continue

        # Score based on proximity (closer = better)
        proximity_score = (1.0 - distance / CLUSTER_RADIUS_KM) * 0.5 + \
                          (1.0 - time_gap / CLUSTER_TIME_WINDOW_MINUTES) * 0.5

        if proximity_score > best_score:
            best_score = proximity_score
            best_cluster = cluster

    if best_cluster:
        return best_cluster["cluster_id"]  # Assign to existing cluster
    else:
        return None  # No matching cluster — will be created by PostgreSQL writer
```

### 13.5 New Cluster Creation

When no existing cluster matches, the event starts a new cluster:

- `ai.cluster_id` is set to `null` in the Kafka message
- The PostgreSQL writer creates a new `event_clusters` row with `member_count = 1`
- The event's `cluster_id` FK is set by the writer on upsert

> Creating clusters at the database level avoids race conditions where multiple
> Spark micro-batches might create duplicate clusters simultaneously.

---

## 14. Cluster Representative

### 14.1 Selection Rules

When the PostgreSQL writer creates or updates a cluster, the **representative event**
(the canonical member) is selected by:

1. **Highest `credibility_score`** — most trustworthy report
2. **Strongest `source_trust_score`** — tiebreaker for equal credibility
3. **Earliest `event_timestamp`** — final tiebreaker (first reporter wins)

### 14.2 Database Impact

The `event_clusters.representative_id` column stores the `event_id` of the
currently selected representative. This is updated by the PostgreSQL writer
on each event upsert to the cluster.

---

## 15. Explainability

### 15.1 Principles

- Every credibility/classification result must produce **human-readable reasons**.
- Reasons must be generated **only from actual available evidence**.
- **Never fabricate evidence.** If a check cannot be performed, say so.
- Reasons are stored in `ai.credibility_reasons` as a list of strings.

### 15.2 Reason Templates

```python
def generate_reasons(factors: dict, event: dict) -> list[str]:
    """Generate human-readable reasons from computed factors."""
    reasons = []

    # Source trust
    trust = factors.get("source_trust", 0.5)
    if trust >= 0.80:
        reasons.append("Source has high configured trust score")
    elif trust >= 0.60:
        reasons.append("Source has moderate configured trust score")
    else:
        reasons.append("Source has low configured trust score")

    # Corroboration
    corrob = count_corroboration(event)
    if corrob >= 2:
        reasons.append(f"{corrob + 1} independent reports detected within proximity")
    elif corrob == 1:
        reasons.append("1 additional corroborating report detected")
    else:
        reasons.append("No independent corroborating reports detected")

    # Weather agreement
    weather_score = factors.get("weather_agreement", 0.5)
    if weather_score >= 0.80:
        reasons.append("Structured weather observations are consistent with the report")
    elif weather_score <= 0.30:
        reasons.append("No corroborating weather observation data found")

    # Temporal
    temporal = factors.get("temporal_consistency", 0.5)
    if temporal >= 0.80:
        reasons.append("Report timestamp is consistent with event occurrence")
    elif temporal <= 0.30:
        reasons.append("Report timestamp shows significant delay from event occurrence")

    # Spatial
    spatial = factors.get("spatial_consistency", 0.5)
    if spatial >= 0.80:
        reasons.append("Reported coordinates are consistent with stated location")
    elif spatial <= 0.30:
        reasons.append("Reported coordinates do not align with stated location")

    # Content quality
    quality = factors.get("content_quality", 0.5)
    if quality >= 0.70:
        reasons.append("Report contains detailed descriptive content")
    elif quality <= 0.30:
        reasons.append("Report description is minimal or absent")

    return reasons
```

### 15.3 Example Outputs

**High-credibility event:**
```json
[
  "Source has high configured trust score",
  "3 independent reports detected within proximity",
  "Structured weather observations are consistent with the report",
  "Report timestamp is consistent with event occurrence",
  "Reported coordinates are consistent with stated location",
  "Report contains detailed descriptive content"
]
```

**Low-credibility event:**
```json
[
  "Source has low configured trust score",
  "No independent corroborating reports detected",
  "No corroborating weather observation data found",
  "Report description is minimal or absent"
]
```

---

## 16. ML Output Contract

### 16.1 Output Fields

The ML library populates these fields in the Canonical Weather Event's `ai` block:

```json
{
  "ai": {
    "classified_category": "flood",
    "classification_confidence": 0.910,
    "duplicate_score": 0.070,
    "credibility_score": 0.840,
    "credibility_reasons": [
      "Source has high configured trust score",
      "3 independent reports detected within proximity",
      "Structured weather observations are consistent with the report"
    ],
    "cluster_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210"
  }
}
```

### 16.2 Schema Mapping (02_DATA_SCHEMA.md §3.6)

| ML Output Field | Schema Field | Type | Range |
|----------------|-------------|------|-------|
| `classified_category` | `ai.classified_category` | enum (§4.1) | One of 12 category values |
| `classification_confidence` | `ai.classification_confidence` | float | 0.0–1.0, 3 decimal places |
| `duplicate_score` | `ai.duplicate_score` | float | 0.0–1.0, 3 decimal places |
| `credibility_score` | `ai.credibility_score` | float | 0.0–1.0, 3 decimal places |
| `credibility_reasons` | `ai.credibility_reasons` | string[] | 0–10 human-readable strings |
| `cluster_id` | `ai.cluster_id` | UUID v4 or null | null if no matching cluster |

### 16.3 Null Handling

If any ML function fails, the corresponding fields are set to `null`:

| Failure | Fields Set to Null | Reason Preserved? |
|---------|-------------------|-------------------|
| Classifier exception | `classified_category`, `classification_confidence` | No (uses adapter hint) |
| Credibility exception | `credibility_score`, `credibility_reasons` | No (empty list) |
| Dedup exception | `duplicate_score` | N/A |
| Clustering exception | `cluster_id` | N/A |

The event is **never dropped** due to ML failure. It proceeds through the
pipeline with null ML outputs.

---

## 17. ML Python Package Structure

```
services/ml/
│
├── __init__.py
│
├── config/
│   ├── ml_config.yaml              # Thresholds, weights, parameters
│   ├── source_trust.yaml           # Source trust scores
│   └── india_cities.json           # City bounding boxes for spatial validation
│
├── classifier/
│   ├── __init__.py
│   ├── interface.py                # BaseClassifier ABC (§4.6)
│   ├── event_classifier.py         # classify_event() entry point — delegates to backend (§4.6)
│   ├── rule_based_classifier.py    # RuleBasedClassifier — Stage 1 (§4.7)
│   ├── trained_classifier.py       # TrainedModelClassifier — Stage 2 (§4.8)
│   ├── hybrid_classifier.py        # HybridClassifier — optional fallback (§4.9)
│   └── rules.py                    # Keyword dictionaries (English, Hindi, Marathi)
│
├── models/
│   └── event_classifier/
│       ├── model.pkl               # Trained sklearn Pipeline (after Stage 2)
│       └── metadata.json           # Model version, metrics, training date
│
├── training/
│   ├── prepare_data.py             # Load + clean labelled data for training
│   ├── train.py                    # Offline training script — NEVER runs at runtime (§19.2)
│   ├── evaluate.py                 # Model evaluation (F1, confusion matrix, comparison)
│   └── data/                       # Labelled training datasets
│       └── weather_events_labelled.csv
│
├── credibility/
│   ├── __init__.py
│   ├── credibility_scorer.py       # score_credibility() entry point
│   └── source_weights.py           # Source trust loading + corroboration logic
│
├── dedup/
│   ├── __init__.py
│   └── duplicate_detector.py       # compute_duplicate_score() entry point
│
├── clustering/
│   ├── __init__.py
│   └── event_clusterer.py          # assign_cluster() entry point
│
├── explainability/
│   ├── __init__.py
│   └── reason_generator.py         # generate_reasons() entry point
│
└── utils/
    ├── __init__.py
    ├── text.py                     # normalize_text(), text_similarity()
    ├── geo.py                      # haversine_km(), city bounding box lookup
    └── time_utils.py               # parse_timestamp(), time_diff_minutes()
```

### 17.1 Design Principles

- **Small, deterministic functions** — each function is pure (same input → same output)
- **No state** — ML functions do not maintain internal state between calls
- **No I/O** — no network calls, no file reads inside functions (config loaded at module init)
- **Testable** — every function can be unit-tested with a simple input/output pair
- **Configurable** — all thresholds and weights loaded from YAML config, not hardcoded

---

## 18. Spark Integration

### 18.1 Per-Record Functions (Pandas UDF)

`classify_event`, `score_credibility`, and `generate_reasons` run as
Pandas UDFs (scalar). They operate on individual rows and are safe for
vectorised execution.

```python
@udf(returnType=StructType([
    StructField("category", StringType()),
    StructField("confidence", DoubleType())
]))
def classify_event_udf(description, category_hint):
    """Pandas UDF wrapper for classify_event."""
    try:
        return classify_event(description, category_hint)
    except Exception as e:
        log.warning(f"classify_event failed: {e}")
        return (category_hint or "other", None)
```

**Why Pandas UDFs?**
- PySpark Pandas UDFs serialize data via Arrow (more efficient than row-at-a-time Python UDFs)
- Per-record functions are independent — no cross-row dependencies
- Safe for vectorised execution within Spark executors

### 18.2 Per-Micro-Batch Functions (foreachBatch)

`compute_duplicate_score` and `assign_cluster` require access to the
**full micro-batch** plus **recent event state**. They run inside
`foreachBatch` handlers.

```python
def process_batch(batch_df, batch_id):
    """Process a micro-batch with ML enrichment."""

    # Step 1: Per-record ML (Pandas UDFs)
    batch_df = batch_df.withColumn("ml_category",
        classify_event_udf(col("description"), col("event_category")))
    batch_df = batch_df.withColumn("ml_credibility",
        score_credibility_udf(struct("*")))
    batch_df = batch_df.withColumn("ml_reasons",
        generate_reasons_udf(struct("*")))

    # Step 2: Collect for window-based ML (safe for MVP micro-batch sizes)
    records = batch_df.collect()
    recent_events = load_recent_events_from_memory(window_minutes=30)
    active_clusters = load_active_clusters_from_memory()

    # Step 3: Per-record window-based ML
    enriched = []
    for record in records:
        rec_dict = record.asDict()
        rec_dict["duplicate_score"] = compute_duplicate_score(rec_dict, recent_events)
        rec_dict["cluster_id"] = assign_cluster(rec_dict, active_clusters)
        enriched.append(rec_dict)

    # Step 4: Write enriched events to Kafka weather.events
    # Step 5: Write Parquet for data lake
    # Step 6: Update in-memory recent events window
```

### 18.3 In-Memory State

For MVP, a small in-memory lookup maintains recent events:

```python
# Global state within the Spark executor process
recent_events_window: list[dict] = []  # Last 30 minutes of events
active_clusters_window: list[dict] = []  # Active cluster centroids
```

- Updated after each successful micro-batch write
- Evicts events older than the configured window
- **Not persisted** — rebuilt from scratch on Spark restart
- Safe for MVP micro-batch sizes (< 1000 events per batch)

---

## 19. Training Architecture (Definitive)

### 19.1 Three-Stage Model

There are exactly **three distinct stages**. They are NOT two separate training pipelines.
They represent a progression from exploration to production.

#### Stage 1 — External Experimentation

| Property | Value |
|----------|-------|
| **What** | Explore algorithms, features, preprocessing, model selection |
| **Where** | Jupyter notebooks, Google Colab, local Python scripts |
| **Output** | Notes, comparison tables, selected approach |
| **Run by** | M4 (any team member with Jupyter) |
| **Frequency** | As needed during development |
| **Deploys to** | Nothing — purely exploratory |

```text
Jupyter Notebook / Colab
  ↓
Try TF-IDF + Logistic Regression
Try TF-IDF + Linear SVM
Compare F1 scores
Select best approach
  ↓
Decision: TF-IDF + Logistic Regression
```

> **This stage never runs inside Spark, Docker, or the live application.**
> It is research and development, not deployment.

#### Stage 2 — Project-Owned Offline Training

| Property | Value |
|----------|-------|
| **What** | Reproducible training script that produces the model artifact |
| **Where** | `training/` directory in the repository |
| **Output** | `models/event_classifier/model.pkl` + `metadata.json` |
| **Run by** | M4, manually or via CI, outside Docker |
| **Frequency** | Once after experimentation, then again when retraining is needed |
| **Deploys to** | Model artifact is placed where Spark can load it |

```text
training/prepare_data.py   → labelled dataset
training/train.py          → trains sklearn Pipeline
training/evaluate.py       → validation metrics
  ↓
models/event_classifier/model.pkl    ← THE artifact
models/event_classifier/metadata.json
  ↓
Placed at MODEL_PATH (default: /opt/models/event_classifier/model.pkl)
  ↓
Spark loads at startup — inference only
```

> **This stage NEVER runs inside Spark Structured Streaming.**
> Training is always an offline, separate process.
> The resulting artifact is a file that the runtime loads.

#### Stage 3 — Runtime Inference

| Property | Value |
|----------|-------|
| **What** | Load pre-trained model, classify incoming events |
| **Where** | Inside Spark worker, via `services/ml/classifier/trained_classifier.py` |
| **Input** | Event description + metadata (from Kafka) |
| **Output** | `classified_category` + `classification_confidence` |
| **Training?** | **NEVER.** Inference only. |

```text
Kafka → Spark → event.description
                    ↓
         services/ml/classifier/trained_classifier.py
                    ↓
         model = joblib.load(MODEL_PATH)
                    ↓
         prediction = model.predict([description])
         confidence = model.predict_proba([description])
                    ↓
         ai.classified_category = prediction
         ai.classification_confidence = max(confidence)
```

### 19.2 What Changes and What Does NOT Change

| Component | Changes? |
|-----------|----------|
| Source adapters | **NO** |
| Canonical Event schema | **NO** |
| Kafka topics | **NO** |
| Kafka envelope | **NO** |
| Spark pipeline architecture | **NO** (only the classifier backend swap) |
| PostgreSQL schema | **NO** |
| FastAPI endpoints | **NO** |
| React frontend | **NO** |
| Docker service topology | **NO** |
| `services/ml/classifier/event_classifier.py` | **NO** — `classify_event()` always works the same way |
| `services/ml/classifier/trained_classifier.py` | **YES** — new file, implements `BaseClassifier` |
| `training/` directory | **NEW** — reproducible offline training scripts |
| `models/event_classifier/` | **NEW** — model artifact storage |
| Spark Dockerfile | **SMALL** — add `scikit-learn` + `joblib` to runtime deps when trained |
| Docker compose | **SMALL** — add model volume mount |
| `.env` config | **YES** — `CLASSIFIER_BACKEND=trained`, `MODEL_PATH=...` |

### 19.3 MVP Decision

**Day 1–2:** Rule-based classifier only. No model training. No labelled dataset needed.

**Day 3–5 (optional):** If a labelled dataset is available and time permits,
train a TF-IDF + Logistic Regression model offline, evaluate it against the
rule-based baseline, and switch `CLASSIFIER_BACKEND=trained` if it wins.

**Critical:** The trained model is a **drop-in replacement**, not an additional component.
The system works with rule-based classification alone. Training is an enhancement, not a dependency.

### 19.4 Runtime Preprocessing Compatibility

> **Critical:** Although training happens offline, incoming production data must be
> prepared using the SAME preprocessing as training before inference.

```text
Training preprocessing:          Runtime preprocessing:
  text → lowercase                 text → lowercase
  text → strip punctuation         text → strip punctuation
  text → Unicode NFKD normalize    text → Unicode NFKD normalize
  text → TF-IDF transform          text → TF-IDF transform (same vectorizer)
  ↓                                ↓
  model.fit(X, y)                  model.predict(X)
```

When using `CLASSIFIER_BACKEND=trained`, the sklearn Pipeline saved during
training includes the TF-IDF vectorizer. This means the same preprocessing
is automatically applied at inference time:

```python
# training/train.py — saves the ENTIRE pipeline
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2))),
    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
])
pipeline.fit(X_train, y_train)
joblib.dump(pipeline, "models/event_classifier/model.pkl")

# trained_classifier.py — loads and uses the pipeline
model = joblib.load(MODEL_PATH)  # includes TF-IDF transform
prediction = model.predict([raw_description])  # preprocessing happens inside pipeline
```

> **Do NOT** preprocess text before calling `model.predict()` when the Pipeline
> already includes a TfidfVectorizer. Double-preprocessing will corrupt features.

### 19.5 Model Artifact Specification

| Property | Value |
|----------|-------|
| Format | `joblib` serialized sklearn `Pipeline` |
| Location | `models/event_classifier/model.pkl` |
| `MODEL_PATH` env var | `/opt/models/event_classifier/model.pkl` (Docker) or local path |
| Expected input | Single string (event description text) |
| Expected output | Category enum string (one of §4.1 values) |
| Confidence | `model.predict_proba()` → max probability |
| Includes preprocessing | Yes — TF-IDF vectorizer is part of the Pipeline |
| Model version | Tracked in `models/event_classifier/metadata.json` |
| Loading | Loaded once at Spark job startup, reused for all records |

**Metadata file (`metadata.json`):**

```json
{
  "model_version": "v1",
  "trained_at": "2026-09-03T14:00:00Z",
  "algorithm": "logistic_regression",
  "features": "tfidf_10000_bigrams",
  "validation_f1": 0.91,
  "rule_based_f1": 0.82,
  "training_samples": 5000,
  "categories": 12,
  "trained_by": "M4",
  "training_script": "training/train.py"
}
```

### 19.6 Hybrid Inference (Trained Model + Rule-Based Fallback)

The `HybridClassifier` (§4.9) implements the confidence-gated fallback:

```text
Trained ML Model
      ↓
Confidence Check
  ├── confidence ≥ MODEL_CONFIDENCE_THRESHOLD → use ML result
  └── confidence < MODEL_CONFIDENCE_THRESHOLD
         OR model artifact unavailable
         OR model loading fails
         OR inference throws exception
                ↓
         Rule-based fallback (§4.7)
                ↓
         Final classification
```

Fallback triggers:

1. Model artifact file not found at `MODEL_PATH`
2. `joblib.load()` fails (corrupted file, missing dependency)
3. `model.predict()` throws an exception
4. Prediction confidence is below `MODEL_CONFIDENCE_THRESHOLD`

```env
CLASSIFIER_BACKEND=hybrid
MODEL_PATH=/opt/models/event_classifier/model.pkl
MODEL_CONFIDENCE_THRESHOLD=0.75
```

> **MVP recommendation:** Start with `CLASSIFIER_BACKEND=rule_based`. Switch to
> `trained` or `hybrid` only after offline evaluation confirms the model exceeds
> the rule-based baseline.

### 19.7 Evaluation Criteria for Switching

Do NOT switch merely because the model works. Compare against the rule-based baseline.

| Metric | Rule-Based Baseline | Trained Model Must Exceed |
|--------|--------------------|--------------------------|
| Overall F1 | Measured during Stage 2 | > Rule-based F1 |
| Per-category F1 | Measured | > 0.80 for all demo categories |
| Worst category | Measured | No category below 0.60 F1 |
| Inference latency | < 5 ms | < 50 ms (acceptable for Spark) |

```text
Rule-based F1 = 0.82  →  Trained model F1 = 0.91  →  SWITCH
Rule-based F1 = 0.82  →  Trained model F1 = 0.79  →  STAY RULE-BASED
Rule-based F1 = 0.82  →  Trained model F1 = 0.91 but hailstorm F1 = 0.55  →  STAY RULE-BASED
```

> **Decision authority:** M4 recommends; M1 approves the switch.
> The switch is a single config change: `CLASSIFIER_BACKEND=trained`.

### 19.8 What Happens to Existing Data

Nothing is deleted. Events classified using rules remain valid historical records.
If a model is later activated:

- **New events** → classified by the trained model
- **Existing events** → retain their rule-based classification (not retroactively changed)
- **Optional reprocessing** → a separate batch job can reclassify old events using the new
  model, but this is NOT automatic and NOT part of the streaming pipeline

---

## 20. Training Dataset

### 20.1 MVP Status

No training dataset exists. No model is trained.

### 20.2 Future Dataset Structure (Optional)

If a labelled dataset is created for evaluation or future model training:

```json
{
  "event_id": "uuid",
  "description": "event text",
  "source_type": "citizen",
  "category_label": "flood",          // Human-verified ground truth
  "severity_label": "high",
  "is_duplicate": false,              // Human-verified
  "cluster_label": "cluster-uuid",    // Human-verified
  "credibility_label": 0.85,          // Derived from admin verification
  "labelled_by": "admin_01",
  "labelled_at": "2026-09-01T10:00:00Z"
}
```

### 20.3 Data Labelling Rules

- Labels come from **admin verification outcomes** (§02_DATA_SCHEMA.md §1.4)
- Synthetic data MUST be clearly labelled as `source_type: "synthetic"` and never presented as genuine
- Simulated social data MUST be labelled as `source_type: "simulated_social"`
- Never represent synthetic data as real citizen reports

---

## 21. Evaluation Metrics

### 21.1 Classification Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Accuracy | Correct classifications / total | ≥ 0.80 |
| Precision (macro) | Average precision across categories | ≥ 0.75 |
| Recall (macro) | Average recall across categories | ≥ 0.70 |
| F1-score (macro) | Harmonic mean of precision and recall | ≥ 0.72 |
| Confusion matrix | Category-by-category breakdown | For analysis only |

### 21.2 Duplicate Detection Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Precision | True duplicates / detected duplicates | ≥ 0.80 |
| Recall | True duplicates found / all true duplicates | ≥ 0.70 |
| F1-score | Harmonic mean | ≥ 0.75 |

### 21.3 Clustering Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Cluster purity | % of cluster members from same real event | ≥ 0.75 (manual inspection for MVP) |

### 21.4 Credibility Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Correlation with admin verification | Spearman correlation between credibility_score and admin "verified" vs "rejected" | ≥ 0.60 |

> **Note:** All benchmark scores are aspirational targets, not commitments.
> No fabricated benchmark scores will be presented. Evaluation uses admin
> verification outcomes as ground truth (where available).

---

## 22. Configuration

### 22.1 Configuration File: `services/ml/config/ml_config.yaml`

```yaml
# Classification
classification:
  high_confidence_threshold: 0.80
  medium_confidence_threshold: 0.60
  low_confidence_threshold: 0.40

# Duplicate Detection
duplicate:
  probable_threshold: 0.85
  possible_threshold: 0.60
  weights:
    text: 0.30
    source_id: 0.20
    source_url: 0.15
    category: 0.15
    time: 0.10
    distance: 0.10

# Clustering
clustering:
  radius_km: 3.0
  time_window_minutes: 30
  max_cluster_size: 50

# Corroboration
corroboration:
  radius_km: 10.0
  window_minutes: 30

# Credibility Weights
credibility:
  weights:
    source_trust: 0.30
    corroboration: 0.25
    weather_agreement: 0.20
    temporal_consistency: 0.10
    spatial_consistency: 0.10
    content_quality: 0.05

# In-Memory Window
spark:
  recent_events_window_minutes: 30
```

### 22.2 Environment Variable Overrides

| Variable | Overrides | Default |
|----------|-----------|---------|
| `CLASSIFIER_BACKEND` | Classifier implementation | `rule_based` |
| `MODEL_PATH` | Trained model artifact path | `/opt/models/event_classifier/model.pkl` |
| `MODEL_CONFIDENCE_THRESHOLD` | Hybrid fallback threshold | 0.75 |
| `ML_CLUSTER_RADIUS_KM` | `clustering.radius_km` | 3.0 |
| `ML_CLUSTER_TIME_WINDOW` | `clustering.time_window_minutes` | 30 |
| `ML_RECENT_EVENTS_WINDOW` | `spark.recent_events_window_minutes` | 30 |

> Configuration is loaded once at Spark job startup. Runtime changes require
> Spark job restart.

---

## 23. Performance Requirements

| Requirement | Target | Notes |
|------------|--------|-------|
| End-to-end latency | ~5 seconds | From Kafka ingestion to PostgreSQL persistence |
| ML per-record processing | < 50 ms | Classification + credibility + explainability |
| ML per-batch processing | < 2 seconds | Duplicate detection + clustering (MVP batch sizes) |
| Memory usage | < 512 MB | In-memory recent events window |
| CPU requirement | **CPU only** | No GPU; no CUDA; no GPU libraries |
| Dependencies (rule-based) | `numpy`, `pyyaml` | No sklearn, no torch, no tensorflow |
| Dependencies (trained model) | `numpy`, `pyyaml`, `scikit-learn`, `joblib` | Added when `CLASSIFIER_BACKEND=trained` |

> ML processing must not become the pipeline bottleneck. If any ML function
> exceeds 100ms per record, it must be profiled and optimised.

---

## 24. Failure Handling

### 24.1 Principle: Never Drop Events

If any ML function fails, the event is preserved with null/default ML outputs.
The event proceeds through the pipeline. ML failure does NOT cause:
- Event rejection
- Dead-letter write
- Pipeline halt
- Data loss

### 24.2 Failure Behaviours

| Failure | Affected Fields | Behaviour | Logging |
|---------|----------------|-----------|---------|
| Classifier exception | `classified_category`, `classification_confidence` | Set to `null`; fall back to adapter's `event.category` | WARNING with traceback |
| Credibility exception | `credibility_score`, `credibility_reasons` | Set to `null` / `[]` | WARNING with traceback |
| Dedup exception | `duplicate_score` | Set to `null` | WARNING with traceback |
| Clustering exception | `cluster_id` | Set to `null` | WARNING with traceback |
| Missing description | Classification | Use category hint only; confidence = 0.30 | INFO |
| Missing coordinates | Spatial scoring, clustering | Neutral scores (0.50); no cluster assignment | INFO |
| Malformed data reaches ML | All fields | Best-effort with available fields; null for missing | WARNING |
| Insufficient evidence | Credibility | Low score with reasons explaining why | INFO |

### 24.3 Spark-Level Protection

ML functions are wrapped in try/except blocks at the UDF/batch handler level:

```python
@udf(returnType=StringType())
def safe_classify(description, category_hint):
    try:
        result = classify_event(description, category_hint)
        return result["category"]
    except Exception as e:
        logger.warning(f"classify_event failed: {e}", exc_info=True)
        return category_hint or "other"
```

---

## 25. Testing Strategy

### 25.1 Unit Tests

**Location:** `services/ml/tests/`

#### Classification Tests (minimum: one per taxonomy category)

| Test | Input | Expected Output |
|------|-------|----------------|
| `test_classify_flood` | "waterlogged roads in Mumbai" | `flood`, confidence ≥ 0.60 |
| `test_classify_heavy_rainfall` | "very heavy rainfall in Nashik" | `heavy_rainfall`, confidence ≥ 0.60 |
| `test_classify_heatwave` | "43°C temperature recorded in Nagpur" | `heatwave`, confidence ≥ 0.60 |
| `test_classify_hailstorm` | "hailstones damaged crops in Nashik" | `hailstorm`, confidence ≥ 0.60 |
| `test_classify_thunderstorm` | "thunder and lightning overnight" | `thunderstorm` or `lightning` |
| `test_classify_cyclone` | "very severe cyclonic storm approaching" | `cyclone`, confidence ≥ 0.60 |
| `test_classify_fog` | "dense fog reducing visibility to 50m" | `fog`, confidence ≥ 0.60 |
| `test_classify_other` | "unusual weather pattern observed" | `other`, confidence < 0.50 |
| `test_classify_empty_description` | `""` | Falls back to category hint |
| `test_classify_hindi_keywords` | "भारी बारिश से बाढ़" | `heavy_rainfall` or `flood` |

#### Credibility Tests

| Test | Scenario | Expected |
|------|----------|---------|
| `test_high_trust_source` | `source_type: "weather_api"` | credibility ≥ 0.70 |
| `test_low_trust_source` | `source_type: "social"` | credibility ≤ 0.65 |
| `test_corroborated_event` | 3 independent reports | credibility ≥ 0.75 |
| `test_no_corroboration` | Single report | credibility based on other factors |
| `test_weather_agreement` | API confirms heavy rain + citizen flood report | weather_factor ≥ 0.80 |
| `test_no_weather_data` | No API data available | weather_factor = 0.30 (neutral) |

#### Deduplication Tests

| Test | Input | Expected |
|------|-------|---------|
| `test_identical_text` | Same description, same time, same location | duplicate_score ≥ 0.85 |
| `test_near_identical_text` | Slight rewording, same time/location | duplicate_score ≥ 0.70 |
| `test_same_source_id` | Same `source_id` | duplicate_score ≥ 0.80 |
| `test_same_location_different_time` | Same coordinates, 2 hours apart | duplicate_score < 0.60 |
| `test_different_events` | Different description, different location | duplicate_score < 0.30 |
| `test_no_recent_events` | Empty recent events list | duplicate_score = 0.0 |

#### Clustering Tests

| Test | Input | Expected |
|------|-------|---------|
| `test_same_location_same_time` | Same city, within 10 min, same category | Same cluster |
| `test_nearby_events` | 2 km apart, within 15 min, compatible category | Same cluster |
| `test_outside_radius` | 10 km apart | Different cluster |
| `test_outside_time_window` | Same location, 2 hours apart | Different cluster |
| `test_incompatible_category` | Same location/time, but heatwave vs flood | Different cluster |
| `test_no_matching_cluster` | First event in area | `cluster_id = null` |

#### Explainability Tests

| Test | Verification |
|------|-------------|
| `test_reasons_match_factors` | Generated reasons correspond to actual computed factor values |
| `test_no_fabricated_evidence` | If no corroboration exists, reasons state "No independent corroborating reports" |
| `test_reasons_not_empty` | Always returns at least 1 reason string |

### 25.2 Test Data

Test data files in `services/ml/tests/fixtures/`:

```
tests/
├── fixtures/
│   ├── mumbai_flood_reports.json       # 5 reports about same flood event
│   ├── nagpur_heatwave_reports.json    # 3 heatwave reports
│   ├── duplicate_reports.json          # 3 near-identical reports
│   ├── low_credibility_reports.json    # Reports from low-trust sources
│   └── edge_cases.json                 # Missing fields, empty descriptions
├── test_classifier.py
├── test_credibility.py
├── test_dedup.py
├── test_clustering.py
└── test_explainability.py
```

---

## 26. Demo Scenarios

### Scenario A — Mumbai Flood (Multi-Source Corroboration)

**Input:** 5 reports from different sources about Mumbai flooding.

| Report | Source | Category Hint | Location |
|--------|--------|--------------|----------|
| 1 | `weather_api` (Open-Meteo) | `heavy_rainfall` | Mumbai, 19.076/72.878 |
| 2 | `rss` (NDTV Weather) | `flood` | Mumbai, 19.080/72.880 |
| 3 | `citizen` (form) | `flood` | Mumbai, 19.075/72.877 |
| 4 | `social` (simulated) | `flood` | Mumbai, 19.070/72.875 |
| 5 | `website` (IMD) | `heavy_rainfall` | Mumbai, 19.078/72.879 |

**Expected Output:**
```
Classification: flood (confidence ≥ 0.85)
Credibility:    ≥ 0.80 (high trust from API + multiple corroboration)
Corroboration:  4 independent reports detected
Cluster:        Same cluster (all within 3 km, 30 min, compatible categories)
Reasons:        "Source has high configured trust score"
                "4 independent reports detected within proximity"
                "Structured weather observations are consistent with the report"
```

### Scenario B — Nagpur Heatwave (API-Dominated)

**Input:** 3 weather API observations with high temperatures.

**Expected Output:**
```
Classification: heatwave (confidence ≥ 0.90)
Credibility:    ≥ 0.90 (weather_api source trust = 0.95)
Corroboration:  2 additional reports
Cluster:        Same cluster
```

### Scenario C — Nashik Hailstorm (Mixed Sources)

**Input:** Citizen report + simulated social + weather API thunderstorm.

**Expected Output:**
```
Classification: hailstorm (confidence ≥ 0.75)
Credibility:    ≥ 0.70 (citizen trust + 1 corroboration + weather agreement)
Cluster:        Same cluster
```

### Scenario D — Duplicate Reports

**Input:** 3 near-identical reports from same source with same text, 2 min apart.

**Expected Output:**
```
Duplicate score: ≥ 0.85 (all 3 flagged as probable duplicates)
Cluster:         Same cluster (for the first unique report)
                 Other reports: duplicate_score high
```

### Scenario E — Suspicious Report

**Input:** Single citizen report with low-trust source, no corroboration, minimal description, coordinates don't match city.

**Expected Output:**
```
Classification: Whatever keywords match (or "other")
Credibility:    ≤ 0.40
Reasons:        "Source has low configured trust score"
                "No independent corroborating reports detected"
                "No corroborating weather observation data found"
                "Reported coordinates do not align with stated location"
                "Report description is minimal or absent"
```

> **Note:** These scenarios produce expected outputs from the defined logic.
> They are NOT hardcoded demo results. The same inputs must produce the same
> outputs deterministically.

---

## 27. Ethical / Data Integrity Rules

1. **Synthetic data must be labelled.** `source_type: "synthetic"` and
   `source_name` containing `"synthetic"`. Never presented as genuine.

2. **Simulated social data must be labelled.** `source_type: "simulated_social"`
   and `platform: "simulated"`. Clearly marked in all views.

3. **Credibility is an assessment, not truth.** The `credibility_score` is a
   computed heuristic. It is NOT a claim about whether the event actually occurred.

4. **AI output must not be presented as guaranteed fact.** Dashboard displays
   must label AI classifications and credibility scores as "AI-assessed" or
   "system-generated".

5. **Citizen reports remain unverified until admin verification.**
   `verification.status` starts as `"pending"` and stays until an admin acts.

6. **No fabricated corroboration.** If no corroborating reports exist, the
   system states "No independent corroborating reports detected" — it does NOT
   claim corroboration that doesn't exist.

7. **No fabricated weather confirmation.** If no weather API data is available
   for comparison, the system states "No corroborating weather observation data found"
   — it does NOT claim weather data confirms an event when it doesn't.

8. **No unnecessary PII.** The ML system processes only event-relevant fields.
   No personal data is collected, stored, or processed by ML modules.

9. **Author IDs must be anonymised.** `social_metadata.author_id` is an
   anonymised identifier, not a real username or profile ID.

10. **Admin verification overrides ML.** If an admin marks an event as
    `verified` or `rejected`, the admin's judgement takes precedence over
    any ML-generated score.

---

## 28. Implementation Checklist (M4)

### Package Structure
- [ ] Create `services/ml/` directory with all subpackages per §17
- [ ] Create `__init__.py` files for all packages
- [ ] Create `config/ml_config.yaml` with all thresholds and weights
- [ ] Create `config/source_trust.yaml` with source trust defaults
- [ ] Create `config/india_cities.json` with Mumbai, Nagpur, Nashik bounding boxes

### Classification (§4–§7)
- [ ] Implement `normalize_text()` in `utils/text.py`
- [ ] Create keyword dictionaries in `classifier/rules.py` (English, Hindi, Marathi)
- [ ] Define `BaseClassifier` ABC in `classifier/interface.py` (§4.6)
- [ ] Implement `classify_event()` dispatcher in `classifier/event_classifier.py` (§4.6)
- [ ] Implement `RuleBasedClassifier` in `classifier/rule_based_classifier.py` (§4.7)
- [ ] Implement confidence calculation
- [ ] Handle empty/missing descriptions (fall back to category hint)
- [ ] **Stage 2 (if time permits):** Create `services/ml/training/` directory
- [ ] **Stage 2:** Implement training script with TF-IDF + Logistic Regression (§4.10)
- [ ] **Stage 2:** Implement `TrainedModelClassifier` in `classifier/trained_classifier.py` (§4.8)
- [ ] **Stage 2:** Validate trained model exceeds rule-based F1 baseline before activation

### Credibility (§8–§9)
- [ ] Implement `score_credibility()` in `credibility/credibility_scorer.py`
- [ ] Implement `compute_source_trust()` with config loading
- [ ] Implement `compute_corroboration()` using recent events window
- [ ] Implement `compute_weather_agreement()` (simplified check)
- [ ] Implement `compute_temporal()` and `compute_spatial()`
- [ ] Implement `compute_content_quality()`

### Corroboration (§10)
- [ ] Implement corroboration counting with independence criteria
- [ ] Implement source deduplication (same source_id, source_url, author_id)
- [ ] Implement category compatibility map

### Duplicate Detection (§11–§12)
- [ ] Implement `compute_duplicate_score()` in `dedup/duplicate_detector.py`
- [ ] Implement `text_similarity()` (Jaccard on normalized keywords)
- [ ] Implement `time_difference_score()` and `geographic_distance_score()`
- [ ] Implement composite scoring with configurable weights

### Clustering (§13–§14)
- [ ] Implement `assign_cluster()` in `clustering/event_clusterer.py`
- [ ] Implement spatial proximity check (Haversine)
- [ ] Implement temporal proximity check
- [ ] Implement category compatibility check
- [ ] Implement cluster size limit

### Explainability (§15)
- [ ] Implement `generate_reasons()` in `explainability/reason_generator.py`
- [ ] Create reason templates for each factor
- [ ] Ensure no fabricated evidence

### Utilities (§17)
- [ ] Implement `haversine_km()` in `utils/geo.py`
- [ ] Implement city bounding box lookup
- [ ] Implement `parse_timestamp()` in `utils/time_utils.py`

### Configuration
- [ ] Load all config from YAML files at module init
- [ ] Support environment variable overrides for key parameters
- [ ] Validate config values on load (ranges, types)

### Unit Tests (§25)
- [ ] `test_classifier.py` — minimum 10 tests (one per category + edge cases)
- [ ] `test_credibility.py` — minimum 6 tests (high/low trust, corroboration, weather)
- [ ] `test_dedup.py` — minimum 6 tests (identical, near-identical, different)
- [ ] `test_clustering.py` — minimum 6 tests (same location/time, outside radius)
- [ ] `test_explainability.py` — minimum 3 tests (reasons match evidence)
- [ ] Create test fixtures in `tests/fixtures/`

### Spark Integration (§18)
- [ ] Verify Pandas UDF wrappers work with Spark schema
- [ ] Verify `foreachBatch` handler collects and processes correctly
- [ ] Verify in-memory state management (recent events window)
- [ ] Verify graceful failure handling (try/except in all UDFs)

### Demo Scenarios (§26)
- [ ] Scenario A: Mumbai flood — verify 5-report corroboration
- [ ] Scenario B: Nagpur heatwave — verify API-dominated classification
- [ ] Scenario C: Nashik hailstorm — verify mixed-source clustering
- [ ] Scenario D: Duplicate reports — verify high duplicate scores
- [ ] Scenario E: Suspicious report — verify low credibility

---

## 29. Cross-Contract Validation

### Against `01_ARCHITECTURE.md`

| Check | Result | Evidence |
|-------|--------|----------|
| ML location: `services/ml/` | ✅ PASS | §17 defines this structure |
| No Docker service for ML | ✅ PASS | §2.2 confirms library-only deployment |
| Function signatures match §6.1 | ✅ PASS | §2.3 lists identical signatures: `classify_event`, `score_credibility`, `compute_duplicate_score`, `assign_cluster`, `generate_reasons` |
| Execution context per function | ✅ PASS | §2.3 matches: per-record Pandas UDF for classify/credibility/reasons; foreachBatch for dedup/clustering |
| ML imported as Python library | ✅ PASS | §2.2 confirms `COPY`-ed into Spark image, imported via `from ml.* import` |
| Published to `weather.events` with `ai.*` populated | ✅ PASS | §16 defines output contract matching this topic's schema |
| No separate ML HTTP service | ✅ PASS | §1.2 explicitly states "No ML HTTP API" |
| Classifier abstraction stable | ✅ PASS | §4.6 defines `BaseClassifier` ABC; Spark calls `classify_event()` which delegates to backend via `CLASSIFIER_BACKEND` env var — no pipeline changes when switching backends |
| Window-based functions need recent events | ✅ PASS | §18.2 defines `foreachBatch` pattern with `load_recent_events_from_memory()` |
| In-memory window (no external state store) | ✅ PASS | §18.3 defines in-memory state, matching architecture §6.2 |

### Against `02_DATA_SCHEMA.md`

| Check | Result | Evidence |
|-------|--------|----------|
| Category enum matches §1.2 | ✅ PASS | §4.1 lists identical 12 values |
| Severity enum matches §1.3 | ✅ PASS | Classification doesn't modify severity; it's preserved from input |
| AI fields match §3.6 | ✅ PASS | §16.2 maps to exact same fields and types |
| `ai.classified_category` type | ✅ PASS | enum (one of 12 categories) — matches schema |
| `ai.classification_confidence` type | ✅ PASS | float 0.0–1.0 — matches schema |
| `ai.duplicate_score` type | ✅ PASS | float 0.0–1.0 — matches schema |
| `ai.credibility_score` type | ✅ PASS | float 0.0–1.0 — matches schema |
| `ai.credibility_reasons` type | ✅ PASS | string[] — matches schema |
| `ai.cluster_id` type | ✅ PASS | UUID v4 or null — matches schema |
| Cluster FK to `event_clusters` table | ✅ PASS | §13.5 explains cluster creation by PostgreSQL writer, avoiding circular dependency |
| Verification status not modified by ML | ✅ PASS | §24.2 confirms ML failure doesn't change `verification.status` |
| `event.category` not modified by ML | ✅ PASS | ML writes to `ai.classified_category`; adapter's `event.category` is preserved |
| DB CHECK constraints satisfied | ✅ PASS | All enum outputs are from valid value sets |

### Against `03_KAFKA_CONTRACT.md`

| Check | Result | Evidence |
|-------|--------|----------|
| ML enriches `weather.events` topic | ✅ PASS | §2.2 Kafka contract confirms: "ai.* fully populated by ML modules" |
| ML enrichment fields match §5.4 | ✅ PASS | §16 output contract matches Kafka §5.4 field-by-field |
| `classify_event()` → `ai.classified_category` | ✅ PASS | §16 maps identically |
| `score_credibility()` → `ai.credibility_score` + `ai.credibility_reasons` | ✅ PASS | §16 maps identically |
| `compute_duplicate_score()` → `ai.duplicate_score` | ✅ PASS | §16 maps identically |
| `assign_cluster()` → `ai.cluster_id` | ✅ PASS | §16 maps identically |
| ML does NOT write to `weather.processed` | ✅ PASS | ML runs inside Spark `foreachBatch`; only `weather.events` is the ML-enriched output |
| Kafka message envelope not affected by ML | ✅ PASS | ML populates `payload.ai.*`; envelope wrapping is Spark's responsibility |

### Against `04_API_CONTRACT.md`

| Check | Result | Evidence |
|-------|--------|----------|
| `GET /events` returns `classified_category`, `classification_confidence` | ✅ PASS | API contract §8 response fields include these |
| `GET /events` returns `credibility_score`, `duplicate_score` | ✅ PASS | API contract §8 response fields include these |
| `GET /events/{id}` returns full `ai.*` block | ✅ PASS | API contract §9 includes `ai.classified_category`, `ai.classification_confidence`, `ai.duplicate_score`, `ai.credibility_score`, `ai.credibility_reasons`, `ai.cluster_id` |
| `GET /events/map` returns `credibility_score` | ✅ PASS | API contract §11 map-optimised response includes it |
| `GET /events/filter` supports `min_credibility` | ✅ PASS | API contract §4.5 lists this filter |
| `GET /events/stats` includes `by_category` aggregation | ✅ PASS | API contract §10 includes category breakdown |
| API does NOT call ML functions | ✅ PASS | API contract §2.1 states "NOT responsible for ML enrichment" |
| ML outputs displayed as AI-assessed | ✅ PASS | §27.4 ethical rule requires this labelling |

### Summary

| Contract | Result |
|----------|--------|
| `01_ARCHITECTURE.md` | ✅ PASS — no conflicts found |
| `02_DATA_SCHEMA.md` | ✅ PASS — no conflicts found |
| `03_KAFKA_CONTRACT.md` | ✅ PASS — no conflicts found |
| `04_API_CONTRACT.md` | ✅ PASS — no conflicts found |

---

## 30. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | ~~ML model selection: rule-based vs. trained classifier~~ | M4 | ✅ **Resolved** — rule-based for MVP per §19.3; trained classifier available as drop-in replacement after offline validation per §19.1–§19.7 |
| 2 | In-memory recent-event window size (minutes) for duplicate/cluster functions | M4 | Open — default 30 minutes per §22; may need tuning based on demo data volume |
| 3 | Specific Open-Meteo weather codes → event category mapping for weather agreement factor | M2/M4 | Open — affects `compute_weather_agreement()` precision |
| 4 | Hindi/Marathi keyword dictionary completeness | M4 | Open — English keywords are primary; Hindi/Marathi are supplementary and can be extended iteratively |
| 5 | City bounding boxes for `india_cities.json` — exact coordinates for Mumbai, Nagpur, Nashik | M4 | Open — need precise bounding boxes for spatial consistency checks |

> **Note:** None of these open questions block Day-1 implementation. All have
> reasonable defaults or can be resolved incrementally during the 5-day sprint.

---

## 31. Final Approval Statement

> This document is the AI/ML source of truth for the MVP. Any change to ML
> inputs, outputs, scoring methodology, thresholds, taxonomy handling,
> clustering logic, or Spark integration must be reflected here before
> implementation.

---

## Appendix A: Dependency Summary

| Package | Version | Purpose | Required? |
|---------|---------|---------|-----------|
| `numpy` | ≥ 1.24 | Numerical operations (Haversine, array math) | **Yes** |
| `pyyaml` | ≥ 6.0 | Config file loading | **Yes** |
| `scikit-learn` | ≥ 1.3 | TF-IDF + Logistic Regression (trained classifier only) | Only when `CLASSIFIER_BACKEND=trained` |
| `joblib` | ≥ 1.3 | Model serialization/deserialization (trained classifier only) | Only when `CLASSIFIER_BACKEND=trained` |
| `torch` / `tensorflow` | — | Not used in MVP | **No** |
| `transformers` (HuggingFace) | — | Not used in MVP | **No** |
| `spacy` / `nltk` | — | Not used in MVP (keyword matching is simpler) | **No** |

> **Stage 1 (rule-based):** Runtime dependencies are `numpy` and `pyyaml` only.
> This keeps the Spark Docker image small and avoids ML framework complexity.
>
> **Stage 2 (trained model):** Add `scikit-learn` and `joblib` to the Spark
> Docker image. Training-only dependencies (`pandas`, `matplotlib`, `jupyter`)
> are NOT included in the runtime image.

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-09-01 | Initial ML specification. Defines all 5 ML components, integration pattern, scoring algorithms, configuration, testing strategy, demo scenarios, and cross-contract validation. Resolves architecture open question #4 (rule-based for MVP). |
| 1.1 | 2026-09-01 | **Classifier abstraction + migration plan:** Added `BaseClassifier` interface (§4.6), `RuleBasedClassifier` (§4.7), `TrainedModelClassifier` (§4.8), `HybridClassifier` (§4.9), training pipeline (§4.10), `CLASSIFIER_BACKEND` / `MODEL_PATH` config, `models/` and `training/` directories, updated package structure (§17), updated dependencies (Appendix A). Migration is a backend swap — no changes to Spark pipeline, Kafka, database, API, or frontend. |
| 1.2 | 2026-09-02 | **Training architecture definitive:** Rewrote §19 as definitive three-stage model (external experimentation → project-owned offline training → runtime inference). Clarified that training NEVER happens inside Spark. Added runtime preprocessing compatibility requirement (§19.4), model artifact specification (§19.5), hybrid inference flow (§19.6), evaluation criteria (§19.7). Updated §17 package structure with top-level `training/` and `models/event_classifier/` paths. Distinguished experimentation from reproducible training scripts. |
