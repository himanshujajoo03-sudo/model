from __future__ import annotations

"""
Training and Retraining Pipeline Tests (§19).
"""

import sys
import os
import json
from pathlib import Path
import pytest

RUN_TRAINING_TESTS = os.environ.get("RUN_TRAINING_TESTS", "false").lower() in {"1", "true", "yes"}
requires_training = pytest.mark.skipif(not RUN_TRAINING_TESTS, reason="training integration tests are opt-in; deployed artifact is tested separately")

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from training.prepare_data import prepare_training_data
from training.train import train_classifier
from training.watch import get_files_fingerprint
from classifier.rules import VALID_CATEGORIES


def test_prepare_data_pipeline(tmp_path):
    out_csv = tmp_path / "cleaned_data.csv"
    df, summary = prepare_training_data(output_path=out_csv)

    assert out_csv.exists()
    assert len(df) > 0
    assert summary["categories_present"] == len(VALID_CATEGORIES)
    assert all(cat in VALID_CATEGORIES for cat in df["category"].unique())


@requires_training
def test_train_and_retrain_artifact_generation(tmp_path):
    out_model_dir = tmp_path / "models" / "event_classifier"
    metadata = train_classifier(output_dir=out_model_dir)

    assert (out_model_dir / "model.pkl").exists()
    assert (out_model_dir / "metadata.json").exists()
    assert metadata["total_samples"] > 0
    assert metadata["categories_count"] == 12
    assert metadata["algorithm"] == "logistic_regression"


@requires_training
def test_trained_classifier_loads_saved_artifact(tmp_path):
    out_model_dir = tmp_path / "models" / "event_classifier"
    train_classifier(output_dir=out_model_dir)

    from classifier.trained_classifier import TrainedModelClassifier
    classifier = TrainedModelClassifier(model_path=str(out_model_dir / "model.pkl"))

    res = classifier.predict("Severe flooding on submerged roads")
    assert res["classified_category"] in ("flood", "heavy_rainfall")
    assert res["classification_confidence"] > 0.40


def test_incoming_file_watcher_fingerprint(tmp_path):
    inc_dir = tmp_path / "incoming"
    inc_dir.mkdir()
    test_file = inc_dir / "new_events.json"
    test_file.write_text('{"events": [{"description": "Rain in Mumbai", "event_type": "rainfall"}]}', encoding="utf-8")

    fp = get_files_fingerprint([inc_dir])
    assert str(test_file.resolve()) in fp
