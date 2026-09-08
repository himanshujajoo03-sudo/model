"""
Train Weather Event Classifier (Standalone for Docker)

Optimized to run in stream-processor container with sklearn 1.3.2
"""

from pathlib import Path
import json
import sys
from datetime import datetime

import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)
from sklearn.model_selection import train_test_split


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DATA_PATH = Path("/tmp/training_data.csv")
MODEL_DIR = Path("/opt/models/event_classifier")
OUTPUT_DIR = MODEL_DIR / "new_model"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_LABELS = [
    "rainfall",
    "heavy_rainfall",
    "flood",
    "thunderstorm",
    "lightning",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_wind",
    "hailstorm",
    "cyclone",
    "other",
]

RANDOM_STATE = 42


# --------------------------------------------------
# Text normalization
# --------------------------------------------------

def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text)
    text = " ".join(text.split())
    return text.strip()


# --------------------------------------------------
# Dataset loading
# --------------------------------------------------

def load_dataset():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training dataset not found: {DATA_PATH}")
    
    df = pd.read_csv(DATA_PATH)
    
    required_columns = {"text", "event_type"}
    missing = required_columns - set(df.columns)
    
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    return df


# --------------------------------------------------
# Dataset validation
# --------------------------------------------------

def clean_dataset(df):
    initial_count = len(df)

    # Normalize text
    df["text"] = df["text"].apply(normalize_text)

    # Remove empty text
    missing_text_count = (df["text"].eq("").sum())
    df = df[df["text"] != ""]

    # Normalize labels
    df["event_type"] = (
        df["event_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Invalid labels
    invalid_mask = ~df["event_type"].isin(ALLOWED_LABELS)
    invalid_label_count = invalid_mask.sum()
    df = df[~invalid_mask]

    # Remove duplicates
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["text", "event_type"])
    duplicates_removed = (before_dedup - len(df))

    report = {
        "initial_records": initial_count,
        "missing_text": int(missing_text_count),
        "invalid_labels": int(invalid_label_count),
        "duplicates_removed": int(duplicates_removed),
        "final_records": len(df),
        "class_distribution": (
            df["event_type"]
            .value_counts()
            .to_dict()
        )
    }

    return df, report


# --------------------------------------------------
# Main training
# --------------------------------------------------

def train():
    print("=" * 70)
    print("Weather Event Classifier Training (sklearn 1.3.2)")
    print("=" * 70)

    # Load
    df = load_dataset()
    print(f"\n✓ Original records: {len(df)}")

    # Clean
    df, quality_report = clean_dataset(df)

    print("\nDataset Quality")
    print("-" * 70)
    for key, value in quality_report.items():
        print(f"  {key}: {value}")

    # Check classes
    missing_classes = set(ALLOWED_LABELS) - set(df["event_type"].unique())
    if missing_classes:
        raise ValueError(f"Missing classes: {missing_classes}")

    # Features / labels
    X = df["text"]
    y = df["event_type"]

    # Split: 80% train, 10% val, 10% test
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=RANDOM_STATE, stratify=y_temp
    )

    print("\nDataset Split")
    print("-" * 70)
    print(f"  Train:      {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")
    print(f"  Test:       {len(X_test)} samples")

    # TF-IDF
    print("\n✓ Training TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_val_tfidf = vectorizer.transform(X_val)
    X_test_tfidf = vectorizer.transform(X_test)

    # Logistic Regression
    print("✓ Training Logistic Regression classifier...")
    classifier = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=RANDOM_STATE
    )

    classifier.fit(X_train_tfidf, y_train)

    # Validation
    y_val_pred = classifier.predict(X_val_tfidf)
    validation_accuracy = accuracy_score(y_val, y_val_pred)

    # Test
    y_test_pred = classifier.predict(X_test_tfidf)
    accuracy = accuracy_score(y_test, y_test_pred)
    precision = precision_score(y_test, y_test_pred, average="macro", zero_division=0)
    recall = recall_score(y_test, y_test_pred, average="macro", zero_division=0)
    macro_f1 = f1_score(y_test, y_test_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_test_pred, average="weighted", zero_division=0)

    cm = confusion_matrix(y_test, y_test_pred, labels=ALLOWED_LABELS)

    # Results
    print("\nEvaluation Results")
    print("-" * 70)
    print(f"  Validation Accuracy: {validation_accuracy:.4f}")
    print(f"  Test Accuracy:       {accuracy:.4f}")
    print(f"  Macro Precision:     {precision:.4f}")
    print(f"  Macro Recall:        {recall:.4f}")
    print(f"  Macro F1:            {macro_f1:.4f}")
    print(f"  Weighted F1:         {weighted_f1:.4f}")

    print("\nClassification Report")
    print("-" * 70)
    print(
        classification_report(
            y_test, y_test_pred, labels=ALLOWED_LABELS, zero_division=0
        )
    )

    # Save artifacts
    import joblib

    # Pipeline (preferred: vectorizer + classifier together)
    pipeline = __import__('sklearn.pipeline', fromlist=['Pipeline']).Pipeline([
        ('vectorizer', vectorizer),
        ('classifier', classifier)
    ])
    
    pipeline_path = OUTPUT_DIR / "classifier_pipeline.joblib"
    joblib.dump(pipeline, pipeline_path)

    # Individual components
    classifier_path = OUTPUT_DIR / "classifier.joblib"
    vectorizer_path = OUTPUT_DIR / "vectorizer.joblib"

    joblib.dump(classifier, classifier_path)
    joblib.dump(vectorizer, vectorizer_path)

    # Labels
    labels_path = OUTPUT_DIR / "labels.json"
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(ALLOWED_LABELS, f, indent=2)

    # Metrics
    metrics = {
        "accuracy": accuracy,
        "macro_precision": precision,
        "macro_recall": recall,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "validation_accuracy": validation_accuracy,
        "confusion_matrix": cm.tolist(),
        "labels": ALLOWED_LABELS
    }

    metrics_path = OUTPUT_DIR / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Metadata
    metadata = {
        "model_name": "weather_event_classifier",
        "version": "1.0.0",
        "algorithm": "LogisticRegression+TF-IDF",
        "sklearn_version": "1.3.2",
        "ngram_range": [1, 2],
        "training_records": len(X_train),
        "validation_records": len(X_val),
        "test_records": len(X_test),
        "total_records": len(df),
        "num_classes": len(ALLOWED_LABELS),
        "class_labels": ALLOWED_LABELS,
        "random_state": RANDOM_STATE,
        "training_date": datetime.now().isoformat(),
        "accuracy": accuracy,
        "macro_f1": macro_f1
    }

    metadata_path = OUTPUT_DIR / "model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n✓ Model Saved")
    print("-" * 70)
    print(f"  Pipeline:  {pipeline_path}")
    print(f"  Classifier: {classifier_path}")
    print(f"  Vectorizer: {vectorizer_path}")
    print(f"  Labels:    {labels_path}")
    print(f"  Metrics:   {metrics_path}")
    print(f"  Metadata:  {metadata_path}")

    print("\n" + "=" * 70)
    print("✓ Training complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        train()
    except Exception as error:
        print(f"\n✗ ERROR: {error}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
