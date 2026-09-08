import os
import pytest

@pytest.fixture(autouse=True)
def isolate_ml_backend():
    os.environ['CLASSIFIER_BACKEND'] = 'rule_based'
    os.environ.pop('MODEL_PATH', None)
    import classifier.event_classifier as ec
    ec._classifier_instance = None
    ec._cached_backend = None
    ec._cached_fingerprint = None
    yield
