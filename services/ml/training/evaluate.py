from __future__ import annotations

"""
Model Evaluation and Benchmark Comparison Script (§19.7, §21.1).
Compares Trained Model against Rule-Based Baseline.
Performs HONEST, leakage-free comparative evaluation on a strictly held-out test split.
"""

import sys
from pathlib import Path
import json
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ..classifier.rules import VALID_CATEGORIES
    from ..classifier.rule_based_classifier import RuleBasedClassifier
    from ..classifier.trained_classifier import TrainedModelClassifier
    from ..config.config_loader import load_ml_config
except ImportError:
    from classifier.rules import VALID_CATEGORIES
    from classifier.rule_based_classifier import RuleBasedClassifier
    from classifier.trained_classifier import TrainedModelClassifier
    from config.config_loader import load_ml_config
from training.prepare_data import prepare_training_data
from training.train import leakage_safe_split


def evaluate_models(data_path: Path | str | None = None, random_state: int = 42) -> dict:
    """
    Run honest comparative evaluation between Rule-Based and Trained models on held-out test data.
    """
    print("=" * 60)
    print("AI/ML Classifier Honest Comparative Evaluation (§19.7)")
    print("=" * 60)

    cfg = load_ml_config()
    df, _ = prepare_training_data(input_path=data_path)

    # Use the exact same configured split ratios and leakage threshold as production training.
    training_cfg = cfg.get("training", {})
    split_ratios = training_cfg.get("split_ratios", {"train": 0.80, "val": 0.10, "test": 0.10})
    train_idx, val_idx, test_idx, _ = leakage_safe_split(
        df, split_ratios, random_state,
        float(training_cfg.get("near_duplicate_threshold", 0.85))
    )
    X_test=df.loc[test_idx,"text"]; y_test=df.loc[test_idx,"category"]
    test_texts=X_test.tolist(); ground_truth=y_test.tolist()
    print(f"Evaluation dataset size: {len(test_texts)} held-out test samples across {len(set(ground_truth))} categories.")

    # 1. Evaluate Rule-Based Classifier on Held-Out Test Set
    rule_classifier = RuleBasedClassifier()
    print("\nRunning Rule-Based Classifier evaluation on held-out test set...")
    rule_preds = []
    for t in test_texts:
        res = rule_classifier.predict(t)
        rule_preds.append(res["classified_category"])

    rule_acc = accuracy_score(ground_truth, rule_preds)
    rule_macro_f1 = f1_score(ground_truth, rule_preds, average="macro", zero_division=0)
    rule_report = classification_report(
        ground_truth, rule_preds, labels=VALID_CATEGORIES, output_dict=True, zero_division=0
    )

    # 2. Evaluate Trained Model Classifier on Held-Out Test Set
    print("Running Trained Model Classifier evaluation on held-out test set...")
    trained_classifier = TrainedModelClassifier()
    trained_preds = []
    for t in test_texts:
        res = trained_classifier.predict(t)
        trained_preds.append(res["classified_category"])

    trained_acc = accuracy_score(ground_truth, trained_preds)
    trained_macro_f1 = f1_score(ground_truth, trained_preds, average="macro", zero_division=0)
    trained_report = classification_report(
        ground_truth, trained_preds, labels=VALID_CATEGORIES, output_dict=True, zero_division=0
    )

    # 3. Decision Rule Assessment (§19.7)
    worst_category_f1 = 1.0
    worst_cat_name = "none"
    for cat in VALID_CATEGORIES:
        if cat in trained_report:
            cat_f1 = trained_report[cat].get("f1-score", 0.0)
            if cat_f1 < worst_category_f1:
                worst_category_f1 = cat_f1
                worst_cat_name = cat

    f1_exceeded = trained_macro_f1 > rule_macro_f1
    worst_cat_ok = worst_category_f1 >= 0.50
    recommend_switch = f1_exceeded and worst_cat_ok

    comparison = {
        "evaluation_samples": len(test_texts),
        "rule_based": {
            "accuracy": round(float(rule_acc), 4),
            "macro_f1": round(float(rule_macro_f1), 4),
        },
        "trained_model": {
            "accuracy": round(float(trained_acc), 4),
            "macro_f1": round(float(trained_macro_f1), 4),
            "worst_category": worst_cat_name,
            "worst_category_f1": round(float(worst_category_f1), 4),
        },
        "decision_criteria": {
            "trained_exceeds_baseline_f1": bool(f1_exceeded),
            "no_critical_category_under_0_50": bool(worst_cat_ok),
            "recommendation": "SWITCH_TO_TRAINED" if recommend_switch else "STAY_RULE_BASED",
        },
    }

    print("\n" + "=" * 40)
    print("HONEST TEST EVALUATION RESULTS:")
    print("=" * 40)
    print(f"Rule-Based Test Macro F1   : {rule_macro_f1:.4f} (Accuracy: {rule_acc:.4f})")
    print(f"Trained Model Test Macro F1: {trained_macro_f1:.4f} (Accuracy: {trained_acc:.4f})")
    print(f"Worst Category ({worst_cat_name}) F1: {worst_category_f1:.4f}")
    print(f"Switch Recommendation      : {comparison['decision_criteria']['recommendation']}")
    print("=" * 60)

    return comparison


if __name__ == "__main__":
    evaluate_models()
