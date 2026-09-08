from __future__ import annotations

"""
Abstract Classifier Interface.
Defined in 05_AI_ML_SPEC.md §4.6.
"""

from abc import ABC, abstractmethod


class BaseClassifier(ABC):
    """Abstract classifier interface."""

    @abstractmethod
    def predict(self, description: str, category_hint: str | None = None) -> dict:
        """
        Classify a weather event.

        Args:
            description: Event description text.
            category_hint: Source adapter's initial category (optional).

        Returns:
            {
                "classified_category": str,        # One of §4.1 enum values
                "classification_confidence": float, # 0.0–1.0
                "category": str,                    # Alias
                "confidence": float                 # Alias
            }
        """
        pass

    @abstractmethod
    def explain(self, description: str, category_hint: str | None = None) -> list[str]:
        """Return human-readable reasons for the classification."""
        pass

