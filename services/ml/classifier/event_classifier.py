from __future__ import annotations

"""
Weather Event Classification Entry Point.
Defined in 05_AI_ML_SPEC.md §4.6.
Centralized backend dispatching and safe fallbacks.
"""

import os
import logging
from typing import Optional

from .interface import BaseClassifier
from .rules import canonicalize_category
from config.config_loader import load_ml_config
try:
    from ..config.config_loader import load_ml_config
except (ImportError, ValueError):
    try:
        from config.config_loader import load_ml_config
    except (ImportError, ValueError):
        from ml.config.config_loader import load_ml_config

logger = logging.getLogger(__name__)

_classifier_instance: Optional[BaseClassifier] = None
_cached_backend: Optional[str] = None
_cached_fingerprint: Optional[tuple] = None


def _get_classifier() -> BaseClassifier:
    """
    Get or instantiate the configured classifier backend.
    Configurable via CLASSIFIER_BACKEND env var ('rule_based', 'trained', 'hybrid').
    Configurable via CLASSIFIER_BACKEND env var or ml_config.yaml ('rule_based', 'trained', 'hybrid').
    Defaults to 'rule_based' per §19.3.
    """
    global _classifier_instance, _cached_backend, _cached_fingerprint
    cfg = load_ml_config()
    class_cfg = cfg.get("classification", {})
    default_backend = class_cfg.get("backend", "rule_based")
    backend = os.environ.get("CLASSIFIER_BACKEND", default_backend).strip().lower()
    model_path = os.environ.get("MODEL_PATH", "")
    threshold = os.environ.get("MODEL_CONFIDENCE_THRESHOLD", str(class_cfg.get("model_confidence_threshold", 0.75)))
    # Include the active artifact mtime so a long-lived Spark worker can pick
    # up an atomically deployed replacement model without restarting.
    model_mtime = None
    if model_path:
        try:
            model_mtime = os.path.getmtime(model_path)
        except OSError:
            pass
    fingerprint = (backend, model_path, threshold, model_mtime)

    if _classifier_instance is not None and _cached_fingerprint == fingerprint:
        return _classifier_instance

    if backend == "rule_based":
        from .rule_based_classifier import RuleBasedClassifier
        _classifier_instance = RuleBasedClassifier()
    elif backend == "trained":
        from .trained_classifier import TrainedModelClassifier
        _classifier_instance = TrainedModelClassifier()
    elif backend == "hybrid":
        from .hybrid_classifier import HybridClassifier
        _classifier_instance = HybridClassifier()
    else:
        logger.warning(f"Unknown CLASSIFIER_BACKEND '{backend}', defaulting to rule_based")
        from .rule_based_classifier import RuleBasedClassifier
        _classifier_instance = RuleBasedClassifier()

    _cached_backend = backend
    _cached_fingerprint = fingerprint
    return _classifier_instance


def classify_event(description: str, category_hint: str | None = None) -> dict:
    """
    Classify a weather event. Public function called by Spark or applications.

    Args:
        description: Event description text.
        category_hint: Source adapter's initial category (optional).

    Returns:
        {
            "classified_category": str,
            "classification_confidence": float,
            "category": str,
            "confidence": float
        }
    """
    canonical_hint = canonicalize_category(category_hint, strict=False)
    try:
        classifier = _get_classifier()
        return classifier.predict(description, canonical_hint)
    except Exception as e:
        # A failed trained artifact must not stop the streaming pipeline or
        # silently downgrade to an arbitrary category hint. The architecture
        # explicitly requires a deterministic rule-based fallback.
        logger.error(f"classify_event backend failed: {e}; using rule-based fallback", exc_info=True)
        try:
            from .rule_based_classifier import RuleBasedClassifier
            return RuleBasedClassifier().predict(description, canonical_hint)
        except Exception as fallback_error:
            logger.error("Rule-based classifier fallback failed: %s", fallback_error, exc_info=True)
            fallback_cat = canonical_hint if canonical_hint else "other"
            return {
                "classified_category": fallback_cat,
                "classification_confidence": 0.0,
                "category": fallback_cat,
                "confidence": 0.0,
            }


def is_high_confidence(confidence: float, threshold: float | None = None) -> bool:
    """Check if classification confidence meets high confidence threshold."""
    if threshold is None:
        cfg = load_ml_config()
        threshold = cfg.get("classification", {}).get("confidence_tiers", {}).get("high", 0.80)
    return float(confidence or 0.0) >= float(threshold)


def load_model():
    """Warm up / load the active classifier backend."""
    _get_classifier()