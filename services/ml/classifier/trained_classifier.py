from __future__ import annotations

"""
Trained ML Model Classifier (Stage 2).
Defined in 05_AI_ML_SPEC.md §4.8, §19.1–§19.5.
Loads canonical pipeline artifacts and performs probability-calibrated inference.
"""

import os
import logging
from pathlib import Path
import joblib
import json
import sklearn
import re

from .interface import BaseClassifier
from .rules import VALID_CATEGORIES, canonicalize_category
from .rule_based_classifier import score_category, RuleBasedClassifier
try:
    from ..utils.text import normalize_text
except (ImportError, ValueError):
    try:
        from utils.text import normalize_text
    except (ImportError, ValueError):
        from ml.utils.text import normalize_text

logger = logging.getLogger(__name__)


class TrainedModelClassifier(BaseClassifier):
    """Supervised ML model-based classifier (TF-IDF + Logistic Regression)."""

    _MODEL_SINGLETON = None
    _VECTORIZER_SINGLETON = None
    _MODEL_LABELS = []
    _MODEL_CACHE = {}

    @classmethod
    def _load_once(cls, model_path: str | None = None):
        """Return a cached classifier for the requested model path.

        The old implementation ignored ``model_path`` after the first load,
        which could make tests/retraining workers accidentally reuse a stale
        model. Keep a small path-keyed cache instead.
        """
        key = str(model_path or os.environ.get("MODEL_PATH") or "<default>")
        cache = getattr(cls, "_MODEL_CACHE", {})
        if key not in cache:
            cache[key] = cls(model_path=model_path)
            cls._MODEL_CACHE = cache
        return cache[key]


    def __init__(self, model_path: str | None = None):
        self._model = None
        self._model_path = model_path or os.environ.get("MODEL_PATH")
        self._load_model()

    def _resolve_model_path(self) -> Path | None:
        if self._model_path:
            p = Path(self._model_path)
            if p.exists():
                return p

        # Candidate standard paths in priority order
        current_dir = Path(__file__).resolve().parent
        root_dir = current_dir.parent

        repo_root = root_dir.parent.parent
        candidates = [
            # Workspace root repository layout: models/event_classifier/
            repo_root / "models" / "event_classifier" / "model.pkl",
            repo_root / "models" / "event_classifier" / "model.joblib",
            repo_root / "models" / "event_classifier" / "classifier_pipeline.joblib",
            # Production deployment layout: ml/models/event_classifier/
            root_dir / "models" / "event_classifier" / "model.pkl",
            root_dir / "models" / "event_classifier" / "model.joblib",
            root_dir / "models" / "event_classifier" / "classifier_pipeline.joblib",
            # Bundled development artifact layout shipped with this package.
            current_dir / "model" / "classifier_pipeline.joblib",
            current_dir / "model" / "classifier.joblib",
            # Container-mounted production artifact.
            Path("/opt/models/event_classifier/model.pkl"),
            Path("/opt/models/event_classifier/model.joblib"),
        ]

        for cand in candidates:
            if cand.exists():
                return cand

        return None

    def _load_model(self):
        resolved = self._resolve_model_path()
        if not resolved:
            raise FileNotFoundError(
                f"Model artifact not found at {self._model_path or 'default paths'}"
            )

        try:
            artifact = joblib.load(resolved)
        except Exception as e:
            raise RuntimeError(f"Failed to load model artifact from {resolved}: {e}") from e

        # Handle either a single Pipeline or a standalone estimator
        self._model = artifact
        self._resolved_path = resolved
        metadata_candidates = [resolved.parent / "metadata.json", resolved.parent / "model_metadata.json"]
        metadata_path = next((p for p in metadata_candidates if p.exists()), metadata_candidates[0])
        self._metadata = {}
        if metadata_path.exists():
            try:
                self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                trained_sklearn = self._metadata.get("sklearn_version")
                if trained_sklearn and trained_sklearn != sklearn.__version__:
                    logger.warning("Model was trained with scikit-learn %s but runtime is %s", trained_sklearn, sklearn.__version__)
            except Exception as e:
                logger.warning("Could not read model metadata %s: %s", metadata_path, e)

        # If vectorizer is separate in legacy structure, check for it
        # Check for legacy decoupled vectorizer if artifact is a bare estimator
        if not hasattr(artifact, "transform") and not hasattr(artifact, "named_steps"):
            vec_path = resolved.parent / "vectorizer.joblib"
            if vec_path.exists():
                self._vectorizer = joblib.load(vec_path)
            else:
                self._vectorizer = None
        else:
            self._vectorizer = None

    def predict(self, description: str, category_hint: str | None = None) -> dict:
        canonical_hint = canonicalize_category(category_hint, strict=False)
        desc_clean = str(description or "").strip()

        # Reject physically implausible heatwave numeric patterns instead of
        # allowing a learned lexical association to promote them.
        numeric_heat = re.search(r"temperature\s+(?:above|over|exceeding)\s+(\d+(?:\.\d+)?)\s*(degrees?)?\s*(c|f|celsius|fahrenheit)?", desc_clean.lower())
        if numeric_heat:
            value=float(numeric_heat.group(1)); unit=(numeric_heat.group(3) or "c").lower()
            if (unit in ("c", "celsius") and value > 60) or (unit in ("f", "fahrenheit") and value > 140):
                return {"classified_category":"other","classification_confidence":0.0,"category":"other","confidence":0.0}

        if not desc_clean:
            cat = canonical_hint if (canonical_hint and canonical_hint in VALID_CATEGORIES) else "other"
            return {
                "classified_category": cat,
                "classification_confidence": 0.0,
                "category": cat,
                "confidence": 0.0,
            }

        try:
            if self._vectorizer is not None:
                features = self._vectorizer.transform([desc_clean])
                raw_pred = str(self._model.predict(features)[0])
                probabilities = self._model.predict_proba(features)[0]
            else:
                raw_pred = str(self._model.predict([desc_clean])[0])
                probabilities = self._model.predict_proba([desc_clean])[0]

            prediction = canonicalize_category(raw_pred, strict=False) or "other"
            confidence = float(max(probabilities))
            confidence = min(max(confidence, 0.0), 1.0)
            # Guard against a high-confidence learned prediction when every
            # explicit mention of that category is locally negated.
            if prediction != "other":
                # Explicit negation needs local, event-aware handling. Use the
                # negation-aware rule layer to resolve a valid positive event
                # instead of letting a learned model follow a negated cue.
                normalized = normalize_text(desc_clean)
                rule_score, _, _ = score_category(normalized, prediction)
                rule_res = RuleBasedClassifier().predict(desc_clean, canonical_hint)
                has_negation = any(
                    n in normalized.split()
                    for n in ("no", "not", "never", "without", "none", "नहीं", "नाही")
                )
                if has_negation:
                    rule_cat = rule_res.get("classified_category", "other")
                    rule_conf = float(rule_res.get("classification_confidence", 0.0))
                    if rule_cat != "other" and rule_cat != prediction and rule_conf >= 0.80:
                        prediction, confidence = rule_cat, rule_conf
                    elif rule_score <= 0.0 and rule_cat == "other":
                        prediction, confidence = "other", 0.0
        except Exception as e:
            logger.warning(f"Prediction error in TrainedModelClassifier: {e}")
            prediction = canonical_hint if canonical_hint else "other"
            confidence = 0.0

        if prediction not in VALID_CATEGORIES:
            prediction = "other"

        return {
            "classified_category": prediction,
            "classification_confidence": round(confidence, 3),
            "category": prediction,
            "confidence": round(confidence, 3),
        }

    def explain(self, description: str, category_hint: str | None = None) -> list[str]:
        res = self.predict(description, category_hint)
        pred = res["classified_category"]
        conf = res["classification_confidence"]
        return [f"Model confidence {conf:.2f} for {pred} based on learned text features"]

