from __future__ import annotations

"""
Hybrid Classifier with Confidence-Gated Fallback.
Defined in 05_AI_ML_SPEC.md §4.9, §19.6.
Uses centralized configuration, deterministic decision policies,
and consistent category_hint semantics.
"""

import logging
import os
from .interface import BaseClassifier
from .rule_based_classifier import RuleBasedClassifier
from .rules import canonicalize_category, categories_are_compatible
try:
    from ..config.config_loader import load_ml_config
except ImportError:
    from config.config_loader import load_ml_config
except (ImportError, ValueError):
    try:
        from config.config_loader import load_ml_config
    except (ImportError, ValueError):
        from ml.config.config_loader import load_ml_config

logger = logging.getLogger(__name__)


class HybridClassifier(BaseClassifier):
    """
    Hybrid classifier combining trained model with deterministic rule-based fallback.
    Uses trained model when confidence >= threshold; falls back to rules otherwise.
    Policy:
      1. If ML confidence >= threshold:
         - Check rule match. If rule strongly conflicts (rule confidence >= 0.85 and incompatible),
           lower confidence slightly to reflect ambiguity. Otherwise, return ML prediction.
      2. If ML confidence < threshold or ML fails:
         - Fallback to deterministic rule-based classifier.
    """

    def __init__(self, threshold: float | None = None):
        self._rules = RuleBasedClassifier()
        if threshold is not None:
            self._threshold = float(threshold)
        else:
            cfg = load_ml_config()
            self._threshold = float(
                os.environ.get(
                    "MODEL_CONFIDENCE_THRESHOLD",
                    cfg.get("classification", {}).get("model_confidence_threshold", 0.75)
                )
            )

        self._model = None
        try:
            from .trained_classifier import TrainedModelClassifier
            self._model = TrainedModelClassifier()
        except Exception as e:
            logger.warning(
                f"TrainedModelClassifier unavailable for HybridClassifier ({e}). "
                "Will use RuleBasedClassifier fallback exclusively."
            )

    def predict(self, description: str, category_hint: str | None = None) -> dict:
        canonical_hint = canonicalize_category(category_hint, strict=False)

        if self._model is not None:
            try:
                ml_res = self._model.predict(description, canonical_hint)
                ml_conf = ml_res["classification_confidence"]
                ml_cat = ml_res["classified_category"]

                if ml_conf >= self._threshold:
                    # Check for strong rule conflict
                    rule_res = self._rules.predict(description, canonical_hint)
                    rule_cat = rule_res["classified_category"]
                    rule_conf = rule_res["classification_confidence"]

                    # If rule found strong incompatible match, temper confidence
                    if (
                        rule_conf >= 0.85 and
                        rule_cat != "other" and
                        rule_cat != ml_cat and
                        not categories_are_compatible(rule_cat, ml_cat)
                    ):
                        logger.info(
                            f"Hybrid classifier conflict: ML={ml_cat} ({ml_conf:.2f}) vs "
                            f"Rule={rule_cat} ({rule_conf:.2f}). Tempering confidence."
                        )
                        tempered_conf = round(max(0.50, (ml_conf + rule_conf) / 2.0 - 0.15), 3)
                        return {
                            "classified_category": ml_cat,
                            "classification_confidence": tempered_conf,
                            "category": ml_cat,
                            "confidence": tempered_conf,
                        }

                    return ml_res
            except Exception as e:
                logger.warning(f"Trained model inference failed in HybridClassifier ({e}); falling back to rules.")

        # Fallback to rule-based classifier
        return self._rules.predict(description, canonical_hint)

    def explain(self, description: str, category_hint: str | None = None) -> list[str]:
        canonical_hint = canonicalize_category(category_hint, strict=False)
        if self._model is not None:
            try:
                ml_res = self._model.predict(description, canonical_hint)
                if ml_res["classification_confidence"] >= self._threshold:
                    return self._model.explain(description, canonical_hint)
            except Exception:
                pass
        return self._rules.explain(description, canonical_hint)
