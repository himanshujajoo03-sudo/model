from __future__ import annotations

"""
Event Classifier Package.
"""

from .event_classifier import classify_event, is_high_confidence
from .interface import BaseClassifier
from .rule_based_classifier import RuleBasedClassifier
from .trained_classifier import TrainedModelClassifier
from .hybrid_classifier import HybridClassifier
from .rules import VALID_CATEGORIES, CATEGORY_PRIORITY, CATEGORY_COMPATIBILITY

__all__ = [
    "classify_event",
    "is_high_confidence",
    "BaseClassifier",
    "RuleBasedClassifier",
    "TrainedModelClassifier",
    "HybridClassifier",
    "VALID_CATEGORIES",
    "CATEGORY_PRIORITY",
    "CATEGORY_COMPATIBILITY",
]