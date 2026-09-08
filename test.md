# Model Integration Testing Guide

**Weather Intelligence Platform — Trained Event Classifier**

This guide walks through every layer of testing, from a quick local smoke test to full end-to-end Docker verification. Run these steps in order to confirm the trained scikit-learn model (TF-IDF + Logistic Regression) is correctly integrated and producing real predictions.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| scikit-learn | 1.7.2 (exact — install below) |
| joblib | 1.3+ |
| pytest | 7+ |
| Docker + Docker Compose | Any recent version |

---

## Step 1 — Verify Model Artifacts Exist

Before anything else, confirm the trained artifacts are present on disk.

```bash
# From the project root
dir Model\classifier\model\
```

**Expected output — all 6 files must be present:**

```
classifier_pipeline.joblib    ← primary artifact (~271 KB)
classifier.joblib              ← fallback artifact
vectorizer.joblib              ← standalone TF-IDF (used with classifier.joblib)
labels.json                    ← 12 category labels
metrics.json                   ← training metrics
model_metadata.json            ← model version info
```

**If any file is missing:** The model artifacts were not committed or were deleted. Do NOT retrain — restore from version control.

---

## Step 2 — Install Required Python Dependencies Locally

```bash
pip install "scikit-learn==1.7.2" "joblib>=1.3" pytest
```

Verify installation:

```bash
python -c "import sklearn, joblib; print('sklearn:', sklearn.__version__, '| joblib:', joblib.__version__)"
```

**Expected output:**
```
sklearn: 1.7.2 | joblib: 1.4.x
```

---

## Step 3 — Quick Python Sanity Check (No pytest needed)

Run this one-liner from the project root to confirm the Pipeline loads and predicts correctly:

```bash
python -c "
import joblib, json
from pathlib import Path

model_dir = Path('Model/classifier/model')
pipeline  = joblib.load(model_dir / 'classifier_pipeline.joblib')
labels    = json.loads((model_dir / 'labels.json').read_text())

test_inputs = [
    'Flash flood submerged roads and waterlogged streets',
    'Cyclone approaching coastal areas with strong winds',
    'Dense fog reducing visibility to near zero',
    'Heatwave conditions with temperature above 44 degrees',
    'Light rain and drizzle expected in the afternoon',
]

print('--- Model Smoke Test ---')
for text in test_inputs:
    label = pipeline.predict([text])[0]
    conf  = max(pipeline.predict_proba([text])[0])
    print(f'  [{conf:.3f}] {label:20s} ← {text[:55]}')
print('--- Done ---')
"
```

**Expected output (category and confidence will vary slightly):**

```
--- Model Smoke Test ---
  [0.999] flood                ← Flash flood submerged roads and waterlogged ...
  [0.999] cyclone              ← Cyclone approaching coastal areas with stron...
  [0.999] fog                  ← Dense fog reducing visibility to near zero
  [0.999] heatwave             ← Heatwave conditions with temperature above 4...
  [0.999] rainfall             ← Light rain and drizzle expected in the after...
--- Done ---
```

**If you see an error here:** Stop — the artifact is corrupt or the sklearn version is wrong.

---

## Step 4 — Run the Automated Integration Test Suite

```bash
python -m pytest tests/test_model_integration.py -v
```

**Expected output:**

```
tests/test_model_integration.py::test_model_directory_exists                    PASSED
tests/test_model_integration.py::test_pipeline_artifact_exists                  PASSED
tests/test_model_integration.py::test_labels_artifact_exists                    PASSED
tests/test_model_integration.py::test_labels_content                            PASSED
tests/test_model_integration.py::test_pipeline_loads                            PASSED
tests/test_model_integration.py::test_preprocessing_whitespace_normalization    PASSED
tests/test_model_integration.py::test_preprocessing_empty_text                  PASSED
tests/test_model_integration.py::test_inference_returns_dict                    PASSED
tests/test_model_integration.py::test_inference_label_is_valid_category         PASSED
tests/test_model_integration.py::test_smoke_inference_correct_category[...]     PASSED  (×9)
tests/test_model_integration.py::test_confidence_in_valid_range                 PASSED
tests/test_model_integration.py::test_trained_classifier_adapter                PASSED
tests/test_model_integration.py::test_trained_classifier_adapter_empty_input    PASSED
tests/test_model_integration.py::test_model_loaded_only_once                    PASSED
tests/test_model_integration.py::test_classify_event_public_api                 PASSED

======================= 23 passed in X.XXs =======================
```

**All 23 tests must pass.** Any failure pinpoints exactly what is broken.

---

## Step 5 — Test the Classifier Adapter Directly (services/ Layer)

This verifies the production adapter (`services/ml/classifier/`) — the exact code used by the Spark stream processor.

```bash
python -c "
import os, sys
from pathlib import Path

# Point to local model artifacts
os.environ['MODEL_PATH']          = str(Path('Model/classifier/model/classifier_pipeline.joblib').resolve())
os.environ['CLASSIFIER_BACKEND']  = 'trained'

# Add services to path (mimics Docker PYTHONPATH)
sys.path.insert(0, str(Path('services').resolve()))

# Reset singletons
import ml.classifier.trained_classifier as tc
import ml.classifier.event_classifier   as ec
tc._MODEL_SINGLETON = None
ec._classifier_instance = None
ec._cached_backend = None

# Run inference
result = ec.classify_event(
    'Severe thunderstorm with heavy rainfall and flooding',
    category_hint='thunderstorm'
)

print('classified_category    :', result['classified_category'])
print('classification_confidence:', result['classification_confidence'])

# Validation assertions
VALID = ['rainfall','heavy_rainfall','flood','thunderstorm','lightning',
         'heatwave','fog','dust_storm','strong_wind','hailstorm','cyclone','other']
assert result['classified_category'] in VALID, 'Invalid category!'
assert 0.0 <= result['classification_confidence'] <= 1.0, 'Confidence out of range!'
assert result['classification_confidence'] != 0.30, 'Still returning stub value — model NOT loaded!'
print()
print('PASS — Real model is producing predictions.')
"
```

**Expected output:**
```
classified_category    : thunderstorm   (or heavy_rainfall / flood — all valid)
classification_confidence: 0.9987        (a real probability, NOT 0.30)

PASS — Real model is producing predictions.
```

**Key check:** Confidence must NOT be `0.30` — that was the hardcoded stub value. Any other value (especially > 0.80) confirms the real model is running.

---

## Step 6 — Test All Three Backends (rule_based / trained / hybrid)

Verify each of the three configurable backends works independently.

```bash
python -c "
import os, sys
from pathlib import Path

os.environ['MODEL_PATH'] = str(Path('Model/classifier/model/classifier_pipeline.joblib').resolve())
sys.path.insert(0, str(Path('services').resolve()))

TEXT  = 'Dense fog with very low visibility on the highway'
BACKENDS = ['rule_based', 'trained', 'hybrid']

for backend in BACKENDS:
    os.environ['CLASSIFIER_BACKEND'] = backend

    import ml.classifier.event_classifier as ec
    import ml.classifier.trained_classifier as tc
    ec._classifier_instance = None
    ec._cached_backend = None
    tc._MODEL_SINGLETON = None

    result = ec.classify_event(TEXT)
    cat    = result['classified_category']
    conf   = result['classification_confidence']
    print(f'  [{backend:10s}]  {cat:20s}  confidence={conf:.3f}')
"
```

**Expected output (all three must return `fog` or a closely related category):**
```
  [rule_based ]  fog                   confidence=0.XXX
  [trained    ]  fog                   confidence=0.999
  [hybrid     ]  fog                   confidence=0.999
```

---

## Step 7 — Test Empty and Edge Case Inputs

```bash
python -c "
import os, sys
from pathlib import Path

os.environ['MODEL_PATH']         = str(Path('Model/classifier/model/classifier_pipeline.joblib').resolve())
os.environ['CLASSIFIER_BACKEND'] = 'trained'
sys.path.insert(0, str(Path('services').resolve()))

import ml.classifier.event_classifier as ec
import ml.classifier.trained_classifier as tc
tc._MODEL_SINGLETON = None
ec._classifier_instance = None
ec._cached_backend = None

edge_cases = [
    ('', None,          'empty string'),
    ('   ', None,       'whitespace only'),
    ('abc', 'flood',    'unclassifiable — hint provided'),
    ('abc', None,       'unclassifiable — no hint'),
]

print('--- Edge Case Tests ---')
for text, hint, label in edge_cases:
    result = ec.classify_event(text, hint)
    cat, conf = result['classified_category'], result['classification_confidence']
    assert cat in ['rainfall','heavy_rainfall','flood','thunderstorm','lightning',
                   'heatwave','fog','dust_storm','strong_wind','hailstorm','cyclone','other']
    print(f'  [{label:30s}]  {cat}  conf={conf}')
print('--- PASS ---')
"
```

**Expected:** No crashes. Empty inputs return `other` (or the hint if one was provided) with confidence `0.0`.

---

## Step 8 — Verify Model is NOT Reloaded Per Request (Singleton)

```bash
python -c "
import os, sys, time
from pathlib import Path

os.environ['MODEL_PATH']         = str(Path('Model/classifier/model/classifier_pipeline.joblib').resolve())
os.environ['CLASSIFIER_BACKEND'] = 'trained'
sys.path.insert(0, str(Path('services').resolve()))

import ml.classifier.trained_classifier as tc
tc._MODEL_SINGLETON = None

import ml.classifier.event_classifier as ec
ec._classifier_instance = None
ec._cached_backend = None

TEXT = 'Heavy rainfall causing waterlogging in the city'

# First call — model should load here
t0 = time.perf_counter()
ec.classify_event(TEXT)
first_call_ms = (time.perf_counter() - t0) * 1000

# Subsequent calls — must reuse singleton, much faster
times = []
for _ in range(10):
    t = time.perf_counter()
    ec.classify_event(TEXT)
    times.append((time.perf_counter() - t) * 1000)

avg_ms = sum(times) / len(times)
print(f'First call (load + predict): {first_call_ms:.1f} ms')
print(f'Avg subsequent calls:        {avg_ms:.2f} ms')
print()

# Singleton identity check
id_before = id(tc._MODEL_SINGLETON)
tc._load_once()
id_after  = id(tc._MODEL_SINGLETON)
assert id_before == id_after, 'FAIL — model was reloaded!'
print('Singleton PASS — model object id unchanged across _load_once() calls.')
"
```

**Expected:** First call is slower (model load). Subsequent calls are much faster. Singleton id is stable.

---

## Step 9 — Build and Verify Docker Image

This confirms the model is correctly baked into the container image.

```bash
# Build the stream-processor image (from project root)
docker build -f services/spark/Dockerfile.stream -t weather-stream-test . --no-cache
```

After the build completes:

```bash
# 1. Verify model artifacts are inside the container
docker run --rm weather-stream-test ls -lh /opt/models/event_classifier/
```

**Expected:**
```
classifier_pipeline.joblib    ~271K
classifier.joblib              ~190K
vectorizer.joblib              ~75K
labels.json                    ~188 bytes
```

```bash
# 2. Verify scikit-learn version inside container
docker run --rm weather-stream-test python3 -c "import sklearn; print(sklearn.__version__)"
```

**Expected:** `1.7.2`

```bash
# 3. Verify import chain resolves correctly inside container
docker run --rm \
  -e CLASSIFIER_BACKEND=trained \
  -e MODEL_PATH=/opt/models/event_classifier/classifier_pipeline.joblib \
  -e PYTHONPATH="/opt/spark/python-deps:/opt/spark:/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip" \
  weather-stream-test \
  python3 -c "
from ml.classifier.event_classifier import classify_event
result = classify_event('Cyclone approaching coastal region with strong winds')
print(result)
assert result['classified_category'] == 'cyclone'
assert result['classification_confidence'] > 0.80
print('PASS — Docker container model inference working.')
"
```

**Expected:**
```
{'classified_category': 'cyclone', 'classification_confidence': 0.9993}
PASS — Docker container model inference working.
```

---

## Step 10 — Full Stack Smoke Test (Docker Compose)

Start the full platform and confirm end-to-end flow.

```bash
# Copy and fill in env values
copy .env.example .env
# Edit .env and set POSTGRES_PASSWORD, JWT_SECRET_KEY, ADMIN_PASSWORD

# Start the platform
docker compose up -d
```

Wait ~60 seconds for all services to become healthy, then:

```bash
# Check stream-processor logs for model initialisation messages
docker logs weather-stream-processor 2>&1 | findstr /i "TrainedModel\|classifier\|model\|loaded"
```

**Expected log lines (in any order):**
```
[TrainedModelClassifier] Loaded Pipeline from /opt/models/event_classifier/classifier_pipeline.joblib
[TrainedModelClassifier] Loaded 12 labels from /opt/models/event_classifier/labels.json
[TrainedModelClassifier] Model integration initialised — framework=scikit-learn, algorithm=LogisticRegression+TF-IDF, classes=12
```

**NOT expected** — any of these means the model failed to load:
```
FileNotFoundError
ModuleNotFoundError
rule_based                    ← would mean CLASSIFIER_BACKEND wasn't applied
classification_confidence: 0.30  ← stub value — integration failed
```

---

## Step 11 — Verify Events in API

After the platform has processed some events:

```bash
# Fetch recent events from the API
curl -s http://localhost:8000/api/v1/events?limit=5 | python -m json.tool
```

In the response, each event should have an `ai` block like:

```json
"ai": {
    "classified_category": "flood",
    "classification_confidence": 0.9987,
    ...
}
```

**Checks:**
- `classified_category` is one of the 12 valid categories
- `classification_confidence` is between `0.0` and `1.0`
- `classification_confidence` is **NOT** `0.30` (that was the stub value)

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: No module named 'joblib'` | scikit-learn not installed | Run Step 2 |
| `FileNotFoundError: Model artifact not found` | `MODEL_PATH` env var wrong or artifacts missing | Check Step 1; verify `MODEL_PATH` points to `classifier_pipeline.joblib` |
| `classification_confidence` is always `0.30` | Old stub code running, not the new implementation | Ensure `services/ml/classifier/trained_classifier.py` was saved correctly |
| `InconsistentVersionWarning` from sklearn | Local sklearn version differs from 1.7.2 | Safe to ignore locally; Docker container pins 1.7.2 |
| `import ml.classifier.xxx` fails in Docker | `PYTHONPATH` missing `/opt/spark` | Check `Dockerfile.stream` ENV PYTHONPATH line includes `/opt/spark` |
| `CLASSIFIER_BACKEND` still `rule_based` | Env var not applied | Set `CLASSIFIER_BACKEND=trained` in shell or `.env` file |

---

## Summary Checklist

```
[ ] Step 1  — All 6 model artifact files present in Model/classifier/model/
[ ] Step 2  — scikit-learn==1.7.2 and joblib installed
[ ] Step 3  — Quick Python smoke test produces real predictions (not errors)
[ ] Step 4  — 23/23 pytest tests PASS
[ ] Step 5  — Services-layer adapter returns real confidence (not 0.30)
[ ] Step 6  — All three backends (rule_based, trained, hybrid) work
[ ] Step 7  — Edge cases (empty input, unclassifiable text) handled without crash
[ ] Step 8  — Singleton confirmed — model not reloaded per request
[ ] Step 9  — Docker image builds; artifacts present at /opt/models/event_classifier/
[ ] Step 10 — docker-compose logs show model initialisation messages
[ ] Step 11 — API events have real classified_category and confidence values
```

All 11 steps passing = the trained model is fully and correctly integrated. ✅



