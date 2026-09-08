"""Shared deterministic test isolation for classifier configuration."""
import os
import pytest

@pytest.fixture(autouse=True)
def reset_classifier_environment():
    os.environ["CLASSIFIER_BACKEND"] = "rule_based"
    os.environ.pop("MODEL_PATH", None)
    for name in ("classifier.event_classifier", "ml.classifier.event_classifier"):
        try:
            import sys
            mod = sys.modules.get(name)
            if mod is not None:
                mod._classifier_instance = None
                mod._cached_backend = None
                mod._cached_fingerprint = None
        except Exception:
            pass
    yield
