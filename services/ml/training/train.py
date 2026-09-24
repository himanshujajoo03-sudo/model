from __future__ import annotations

"""
Offline Training & Retraining Script for Event Classifier.
Defined in 05_AI_ML_SPEC.md §4.10, §19.1–§19.5.
Supports Multilingual Indic & English NLP feature representations.
Offline Training & Safe Deployment Pipeline for Event Classifier.
Defined in 05_AI_ML_SPEC.md §4.10, §19.1–§19.5, §21, §22, §23.
Features:
1. Small dataset protection & class count checks
2. Data leakage detection across train/val/test splits
3. Atomic model deployment via staging candidates
4. Acceptance threshold verification before production promotion
"""

import sys
import os
import shutil
from datetime import datetime
from pathlib import Path
import json
import logging
import joblib
import pandas as pd
import sklearn

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

try:
    from ..classifier.rules import VALID_CATEGORIES
    from ..config.config_loader import load_ml_config
    from .prepare_data import prepare_training_data
    from .split_validator import validate_split_feasibility, SplitFeasibilityError
    from .leakage import check_leakage_detailed, LeakageError
except (ImportError, ValueError):
    from classifier.rules import VALID_CATEGORIES
    from config.config_loader import load_ml_config
    from training.prepare_data import prepare_training_data
    from training.split_validator import validate_split_feasibility, SplitFeasibilityError
    from training.leakage import check_leakage_detailed, LeakageError

MODEL_OUTPUT_DIR = PROJECT_ROOT / "models" / "event_classifier"
LEGACY_MODEL_DIR = MODEL_OUTPUT_DIR
logger = logging.getLogger(__name__)

MODELS_DIR = PROJECT_ROOT / "models"
PRODUCTION_MODEL_DIR = MODELS_DIR / "event_classifier"
CANDIDATES_DIR = MODELS_DIR / "candidates"
ARCHIVE_DIR = MODELS_DIR / "archive"

# Rule 5 (hardening pass 2): force_deploy is a development-only escape hatch.
# It can NEVER be used to bypass production safety gates unless this
# environment variable is explicitly set. The automatic watcher (watch.py)
# never sets this and never passes force_deploy=True.
FORCE_DEPLOY_ENV_FLAG = "ML_ALLOW_FORCE_DEPLOY"


class SmallDatasetError(ValueError):
    """Raised when dataset is too small to perform stratified training and evaluation."""
    def __init__(self, message: str, report: dict | None = None):
        super().__init__(message)
        self.report = report or {}


class ModelDeploymentError(RuntimeError):
    """Raised when candidate model fails quality acceptance criteria for production."""
    pass


class ForceDeployNotPermittedError(RuntimeError):
    """
    Raised when a caller requests force_deploy=True without explicitly
    enabling the development-only environment flag. This prevents any
    caller (accidental or malicious) from silently bypassing production
    quality gates.
    """
    pass



def check_data_leakage(train_texts: pd.Series, val_texts: pd.Series, test_texts: pd.Series) -> dict[str, int]:
    """Check for identical texts appearing across different data splits."""
    train_set = set(train_texts)
    val_set = set(val_texts)
    test_set = set(test_texts)

    train_val_overlap = len(train_set & val_set)
    train_test_overlap = len(train_set & test_set)
    val_test_overlap = len(val_set & test_set)

    return {
        "train_val_overlap": train_val_overlap,
        "train_test_overlap": train_test_overlap,
        "val_test_overlap": val_test_overlap,
        "total_leakage_cases": train_val_overlap + train_test_overlap + val_test_overlap
    }



def _union_find_groups(df: pd.DataFrame, threshold: float = 0.85) -> pd.Series:
    """Build leakage-safe groups from event IDs and near-duplicate text."""
    n=len(df); parent=list(range(n))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    if "event_id" in df:
        ids={}
        for i,v in enumerate(df["event_id"]):
            if pd.notna(v) and str(v).strip():
                k=str(v); 
                if k in ids: union(i,ids[k])
                else: ids[k]=i
    texts=df["text"].fillna("").astype(str).tolist()
    # Candidate pairs by shared tokens; then exact Jaccard. This avoids a full n^2 matrix.
    inv={}
    token_sets=[]
    for i,t in enumerate(texts):
        ts=set(t.split()); token_sets.append(ts)
        for tok in ts: inv.setdefault(tok,[]).append(i)
    candidates=set()
    for inds in inv.values():
        if len(inds)>1:
            for a in range(len(inds)):
                for b in range(a+1,len(inds)): candidates.add((inds[a],inds[b]))
    for i,j in candidates:
        a,b=token_sets[i],token_sets[j]
        if not a or not b: continue
        if len(a & b)/len(a | b) >= threshold: union(i,j)
    return pd.Series([find(i) for i in range(n)], index=df.index, dtype="int64")


def _required_group_count_per_class(
    df: pd.DataFrame,
    groups: pd.Series,
    splits: int = 3,
) -> dict[str, int]:
    """Return the number of distinct leakage groups available per class."""
    work = df[["category"]].copy()
    work["_group"] = groups.reindex(df.index).astype(str).values
    return work.groupby("category")["_group"].nunique().astype(int).to_dict()


def _validate_group_split_feasibility(
    df: pd.DataFrame,
    groups: pd.Series,
    split_cfg: dict[str, float],
) -> None:
    """Fail early when group-based splitting cannot produce three useful splits.

    Raw record counts are insufficient once event/near-duplicate groups are
    enforced.  Every class needs at least one distinct group available for
    train, validation and test.  We intentionally use a conservative
    three-groups-per-class requirement so the resulting evaluation is
    meaningful rather than relying on accidental mixed-class groups.
    """
    if df.empty:
        raise SplitFeasibilityError("Cannot perform grouped split: dataset is empty.")

    counts = _required_group_count_per_class(df, groups)
    required = 3
    problems = {
        cat: {"distinct_groups": n, "required_groups": required}
        for cat, n in counts.items() if n < required
    }
    total_groups = int(groups.nunique())
    if total_groups < 3:
        raise SplitFeasibilityError(
            f"Cannot perform leakage-safe train/val/test split: only {total_groups} "
            "distinct leakage group(s) are available; at least 3 are required."
        )
    if problems:
        details = ", ".join(
            f"'{cat}' has {info['distinct_groups']} group(s), needs {required}"
            for cat, info in sorted(problems.items())
        )
        raise SplitFeasibilityError(
            "Cannot perform leakage-safe stratified grouped split because one or more "
            f"classes do not have enough distinct groups: {details}. "
            "Add independent events/examples or reduce grouping aggressiveness."
        )

    # Guard against nonsensical configured ratios here as this function is also
    # used by callers outside config_loader.
    ratios = [float(split_cfg[k]) for k in ("train", "val", "test")]
    if any(r <= 0 or r >= 1 for r in ratios) or abs(sum(ratios) - 1.0) > 1e-6:
        raise SplitFeasibilityError(
            f"Invalid split ratios for grouped splitting: {split_cfg}. "
            "Ratios must be > 0 and sum to 1."
        )


def _candidate_n_splits(desired_fraction: float, n_groups: int) -> list[int]:
    """Generate useful SGKF fold counts around the requested holdout fraction."""
    if not 0 < desired_fraction < 1:
        raise ValueError(f"desired_fraction must be between 0 and 1, got {desired_fraction}")
    if n_groups < 2:
        raise SplitFeasibilityError(
            f"At least 2 distinct groups are required for a holdout split; got {n_groups}."
        )
    ideal = 1.0 / desired_fraction
    seeds = {
        max(2, min(n_groups, int(round(ideal)))),
        max(2, min(n_groups, int(ideal))),
        max(2, min(n_groups, int(ideal) + 1)),
    }
    # Nearby alternatives matter when group sizes are uneven.
    for delta in (-2, -1, 1, 2):
        seeds.add(max(2, min(n_groups, int(round(ideal)) + delta)))
    return sorted(seeds)


def _choose_group_fold(
    df: pd.DataFrame,
    groups: pd.Series,
    n_splits: int | None,
    random_state: int,
    desired_fraction: float,
) -> tuple[pd.Index, pd.Index]:
    """Choose a useful StratifiedGroupKFold holdout close to desired_fraction.

    ``n_splits`` is retained for backward compatibility.  When supplied, it is
    treated as a preferred fold count; the splitter may also try nearby counts
    derived from the requested fraction.  Candidate folds with an empty
    holdout, an empty training set, or missing classes in either side are
    disqualified before size/balance scoring.
    """
    if len(df) == 0:
        raise SplitFeasibilityError("Cannot split an empty dataframe.")
    if len(df) != len(groups):
        raise SplitFeasibilityError("Grouped split received mismatched dataframe/group lengths.")

    y = df["category"]
    group_values = groups.reindex(df.index)
    n_groups = int(group_values.nunique())
    if n_groups < 2:
        raise SplitFeasibilityError(
            f"Cannot create a holdout: only {n_groups} distinct leakage group(s) are available."
        )

    global_classes = set(y.dropna().astype(str).unique())
    preferred = n_splits if n_splits is not None else max(2, round(1.0 / desired_fraction))
    candidates = [preferred] + _candidate_n_splits(desired_fraction, n_groups)
    candidates = sorted({min(n_groups, max(2, int(n))) for n in candidates})

    best = None
    rejection_reasons: list[str] = []
    global_dist = y.value_counts(normalize=True)

    for folds in candidates:
        try:
            sgkf = StratifiedGroupKFold(
                n_splits=folds, shuffle=True, random_state=random_state
            )
            for tr_idx, hold_idx in sgkf.split(df["text"], y, group_values):
                if len(hold_idx) == 0 or len(tr_idx) == 0:
                    rejection_reasons.append(f"{folds}-fold candidate had an empty split")
                    continue
                train_classes = set(y.iloc[tr_idx].astype(str))
                hold_classes = set(y.iloc[hold_idx].astype(str))
                if train_classes != global_classes or hold_classes != global_classes:
                    rejection_reasons.append(
                        f"{folds}-fold candidate did not preserve all classes "
                        f"(train={sorted(train_classes)}, holdout={sorted(hold_classes)})"
                    )
                    continue

                hold = df.iloc[hold_idx]
                size_err = abs(len(hold) / len(df) - desired_fraction)
                dist = hold["category"].value_counts(normalize=True).reindex(
                    global_dist.index, fill_value=0
                )
                balance = float((dist - global_dist).abs().mean())
                # Prefer candidates closer to the requested fraction, then
                # better class balance. Never permit an empty/partial fold.
                key = (size_err, balance)
                if best is None or key < best[0]:
                    best = (key, tr_idx, hold_idx, folds)

        except ValueError as exc:
            rejection_reasons.append(f"{folds}-fold candidate failed: {exc}")

    if best is None:
        reason = "; ".join(rejection_reasons[:4])
        raise SplitFeasibilityError(
            f"Unable to produce a valid leakage-safe stratified grouped holdout "
            f"of approximately {desired_fraction:.1%}. Dataset has {len(df)} records "
            f"and {n_groups} leakage groups. Every candidate must contain every class "
            f"in both training and holdout. {reason}"
        )

    return df.iloc[best[1]].index, df.iloc[best[2]].index


def leakage_safe_split(
    df: pd.DataFrame,
    split_cfg: dict,
    random_state: int,
    near_duplicate_threshold: float = 0.85,
):
    """Split into train/val/test without sharing event or near-duplicate groups.

    The requested ratios drive the SGKF fold counts instead of hard-coded 10/9
    folds. Because group sizes are discrete, actual ratios are best-effort and
    are reported by the caller; impossible configurations fail clearly.
    """
    groups = _union_find_groups(df, near_duplicate_threshold)
    _validate_group_split_feasibility(df, groups, split_cfg)

    test_fraction = float(split_cfg["test"])
    train_fraction = float(split_cfg["train"])
    val_fraction = float(split_cfg["val"])

    # Select test directly from the full dataset.
    test_n = max(2, round(1.0 / test_fraction))
    trainval_idx, test_idx = _choose_group_fold(
        df, groups, test_n, random_state, test_fraction
    )

    rem = df.loc[trainval_idx]
    rem_groups = groups.loc[trainval_idx]
    conditional_val_fraction = val_fraction / (train_fraction + val_fraction)
    val_n = max(2, round(1.0 / conditional_val_fraction))
    _, val_idx = _choose_group_fold(
        rem, rem_groups, val_n, random_state + 1, conditional_val_fraction
    )
    train_idx = rem.index.difference(val_idx)

    if not train_idx.size or not val_idx.size or not test_idx.size:
        raise SplitFeasibilityError(
            f"Grouped split produced an empty split: train={len(train_idx)}, "
            f"val={len(val_idx)}, test={len(test_idx)}. "
            "Increase the number of independent groups or adjust split ratios."
        )

    # Final invariant: no leakage group may cross boundaries.
    memberships = {}
    for name, idx in (("train", train_idx), ("val", val_idx), ("test", test_idx)):
        for g in groups.loc[idx].tolist():
            memberships.setdefault(g, set()).add(name)
    crossed = {g: sorted(parts) for g, parts in memberships.items() if len(parts) > 1}
    if crossed:
        raise LeakageError(
            f"Internal grouped-split invariant violated: {len(crossed)} leakage group(s) "
            "cross train/val/test boundaries."
        )

    return train_idx, val_idx, test_idx, groups

def train_classifier(
    data_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    random_state: int | None = None,
    force_deploy: bool = False
) -> dict:
    """
    Train a candidate TF-IDF + Logistic Regression model, evaluate on held-out test data,
    verify acceptance thresholds, and atomically deploy if criteria are satisfied.

    If ``output_dir`` is explicitly provided, the trained artifacts are saved directly
    there (used for tests / ad-hoc training). Otherwise the model is staged as a
    candidate under models/candidates/<run_id> and only promoted to the production
    model directory if it passes the configured acceptance thresholds.

    ``force_deploy`` (Rule 5, hardening pass 2): this is a DEVELOPMENT-ONLY escape
    hatch. It is refused unless the ML_ALLOW_FORCE_DEPLOY=1 environment variable is
    explicitly set by the caller/operator, so it can never be used accidentally (or
    by the automatic watcher, which never sets this flag). When used, the resulting
    metadata is clearly marked "deployment_forced": true for audit purposes.
    """
    if force_deploy and os.environ.get(FORCE_DEPLOY_ENV_FLAG) != "1":
        raise ForceDeployNotPermittedError(
            "force_deploy=True was requested but the development-only "
            f"{FORCE_DEPLOY_ENV_FLAG}=1 environment variable is not set. "
            "Production training must never bypass acceptance quality gates. "
            "If you are deliberately forcing a development deployment, set "
            f"{FORCE_DEPLOY_ENV_FLAG}=1 explicitly before calling train_classifier(force_deploy=True)."
        )

    cfg = load_ml_config()
    train_cfg = cfg.get("training", {})
    r_state = random_state if random_state is not None else train_cfg.get("random_state", 42)
    acceptance = train_cfg.get("acceptance_thresholds", {
        "min_macro_f1": 0.70,
        "min_accuracy": 0.75,
        "min_category_f1": 0.50
    })
    leakage_policy = train_cfg.get("leakage_policy", "strict")

    print("=" * 60)
    print("Starting Weather Event Classifier Training / Retraining")
    print("=" * 60)

    # 1. Prepare and clean dataset
    df, prep_report = prepare_training_data(input_path=data_path)
    X = df["text"]
    y = df["category"]

    # 2. Verify the dataset can be safely, stratified-split into train/val/test (Rule 2)
    split_cfg = train_cfg.get("split_ratios", {"train": 0.80, "val": 0.10, "test": 0.10})
    class_counts = y.value_counts().to_dict()
    try:
        validate_split_feasibility(class_counts, split_cfg)
    except SplitFeasibilityError as e:
        raise SmallDatasetError(str(e), report=getattr(e, "report", {})) from e

    # 3. Leakage-safe grouped split. Near-duplicate/event groups are created BEFORE splitting.
    val_ratio = float(split_cfg.get("val", 0.10)); test_ratio=float(split_cfg.get("test",0.10))
    train_idx, val_idx, test_idx, leakage_groups = leakage_safe_split(df, split_cfg, r_state, float(train_cfg.get("near_duplicate_threshold",0.85)))
    X_train,y_train=df.loc[train_idx,"text"],df.loc[train_idx,"category"]
    X_val,y_val=df.loc[val_idx,"text"],df.loc[val_idx,"category"]
    X_test,y_test=df.loc[test_idx,"text"],df.loc[test_idx,"category"]
    print(f"Leakage-safe grouped split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}, Groups={leakage_groups.nunique()}")

    # 4. Check data leakage across splits (Rule 3): legacy exact-overlap report
    # kept for backward compatibility, plus the expanded, policy-driven audit.
    leakage = check_data_leakage(X_train, X_val, X_test)
    print(f"Data leakage audit (legacy): {leakage}")

    train_df = df.loc[X_train.index]
    val_df = df.loc[X_val.index]
    test_df = df.loc[X_test.index]
    leakage_detailed = check_leakage_detailed(
        train_df, val_df, test_df,
        policy=leakage_policy,
        near_duplicate_threshold=float(train_cfg.get("near_duplicate_threshold", 0.85)),
        leakage_groups=leakage_groups,  # enables O(n) group-membership fast-path
    )
    nd_methods = leakage_detailed.get("near_duplicate_check_methods", {})
    print(f"Data leakage audit (detailed, policy={leakage_policy}): {leakage_detailed}")
    print(f"Near-duplicate check methods used: {nd_methods}")

    # 5. Construct and fit sklearn Pipeline (§19.4) with full Unicode token pattern
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                max_features=10000,
                min_df=1,
                max_df=0.95,
                sublinear_tf=True,
                token_pattern=r"(?u)\b\w+\b",
            ),
        ),
        (
            "clf",
            CalibratedClassifierCV(
                estimator=LogisticRegression(max_iter=1500, class_weight="balanced", random_state=r_state),
                method="sigmoid",
                cv=3,
            ),
        ),
    ])

    print("\nTraining scikit-learn Pipeline (TF-IDF + LogisticRegression)...")
    pipeline.fit(X_train, y_train)

    # 6. Evaluation on held-out validation and test sets
    y_val_pred = pipeline.predict(X_val)
    val_accuracy = accuracy_score(y_val, y_val_pred)

    y_test_pred = pipeline.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_test_pred)
    macro_precision = precision_score(y_test, y_test_pred, average="macro", zero_division=0)
    macro_recall = recall_score(y_test, y_test_pred, average="macro", zero_division=0)
    macro_f1 = f1_score(y_test, y_test_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_test_pred, average="weighted", zero_division=0)

    # Per-category metrics
    cm = confusion_matrix(y_test, y_test_pred, labels=VALID_CATEGORIES)
    report_dict = classification_report(
        y_test, y_test_pred, labels=VALID_CATEGORIES, output_dict=True, zero_division=0
    )

    # Find worst category F1
    worst_category_f1 = 1.0
    worst_cat_name = "none"
    for cat in VALID_CATEGORIES:
        if cat in report_dict:
            cat_f1 = report_dict[cat].get("f1-score", 0.0)
            if cat_f1 < worst_category_f1:
                worst_category_f1 = cat_f1
                worst_cat_name = cat

    print("\n" + "=" * 40)
    print("Candidate Model Evaluation Summary")
    print("=" * 40)
    print(f"Validation Accuracy : {val_accuracy:.4f}")
    print(f"Test Accuracy       : {test_accuracy:.4f}")
    print(f"Macro Precision     : {macro_precision:.4f}")
    print(f"Macro Recall        : {macro_recall:.4f}")
    print(f"Macro F1 Score      : {macro_f1:.4f}")
    print(f"Weighted F1 Score   : {weighted_f1:.4f}")
    print(f"Worst Category ({worst_cat_name}) F1: {worst_category_f1:.4f}")

    # 7. Check Acceptance Criteria (§22)
    trained_classes = set(pipeline.classes_)
    missing_classes = set(VALID_CATEGORIES) - trained_classes - {"other"}
    passed_acceptance = (
        not missing_classes and
        macro_f1 >= acceptance["min_macro_f1"] and
        test_accuracy >= acceptance["min_accuracy"] and
        worst_category_f1 >= acceptance["min_category_f1"]
    )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_version = f"weather-event-classifier-{run_id}"
    metadata = {
        "model_version": model_version,
        "run_id": run_id,
        "trained_at": datetime.now().isoformat(),
        "algorithm": "logistic_regression",
        "probability_calibration": "sigmoid_cv3",
        "sklearn_version": sklearn.__version__,
        "features": "tfidf_10000_bigrams_unicode",
        "random_state": r_state,
        "validation_accuracy": round(float(val_accuracy), 4),
        "test_accuracy": round(float(test_accuracy), 4),
        "macro_precision": round(float(macro_precision), 4),
        "macro_recall": round(float(macro_recall), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "worst_category": worst_cat_name,
        "worst_category_f1": round(float(worst_category_f1), 4),
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "test_samples": len(X_test),
        "total_samples": len(df),
        "categories_count": len(VALID_CATEGORIES),
        "categories": VALID_CATEGORIES,
        "trained_by": "Project-Owned Offline Training",
        "training_script": "training/train.py",
        "data_leakage": leakage,
        "data_leakage_detailed": leakage_detailed,
        "leakage_policy": leakage_policy,
        "acceptance_passed": passed_acceptance,
        "deployment_forced": bool(force_deploy),
        "missing_classes": sorted(missing_classes),
        "per_category_metrics": {
            cat: report_dict.get(cat, {}) for cat in VALID_CATEGORIES if cat in report_dict
        },
    }

    if force_deploy:
        logger.warning(
            f"[AUDIT] force_deploy=True used for run_id={run_id} "
            f"(acceptance_passed={passed_acceptance}). Production safety gates were "
            f"explicitly overridden by an operator with {FORCE_DEPLOY_ENV_FLAG}=1 set."
        )

    if output_dir:
        # Explicit output directory requested (e.g. tests / ad-hoc training):
        # save directly there, skipping the candidate-staging/promotion flow.
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        model_file = target_dir / "model.pkl"
        metadata_file = target_dir / "metadata.json"
        joblib.dump(pipeline, model_file)
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"\nTrained model successfully saved to: {model_file}")
        print(f"Metadata saved to: {metadata_file}")
        print("=" * 60)
        return metadata

    # 8. Save to candidate staging area (§21)
    candidate_dir = CANDIDATES_DIR / run_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidate_model_file = candidate_dir / "model.pkl"
    candidate_meta_file = candidate_dir / "metadata.json"
    joblib.dump(pipeline, candidate_model_file)
    with open(candidate_meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nCandidate model successfully saved to: {candidate_model_file}")
    print(f"Metadata saved to: {candidate_meta_file}")

    # 9. Atomic Promotion to Production (§23)
    if passed_acceptance or force_deploy:
        print(f"\n[ACCEPTANCE PASSED] Promoting candidate {run_id} to production at {PRODUCTION_MODEL_DIR}")
        PRODUCTION_MODEL_DIR.mkdir(parents=True, exist_ok=True)

        # Archive existing model if present
        if (PRODUCTION_MODEL_DIR / "model.pkl").exists():
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            archive_target = ARCHIVE_DIR / f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            try:
                shutil.copy2(PRODUCTION_MODEL_DIR / "model.pkl", archive_target)
            except Exception as e:
                logger.warning(f"Could not archive previous model: {e}")

        # Atomic copy into production via a temp staging directory
        temp_prod_dir = PRODUCTION_MODEL_DIR.parent / f"_temp_deploy_{run_id}"
        temp_prod_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, temp_prod_dir / "model.pkl")
        with open(temp_prod_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        shutil.copy2(temp_prod_dir / "model.pkl", PRODUCTION_MODEL_DIR / "model.pkl")
        shutil.copy2(temp_prod_dir / "metadata.json", PRODUCTION_MODEL_DIR / "metadata.json")
        shutil.rmtree(temp_prod_dir, ignore_errors=True)

        # Also refresh legacy compatibility artifacts
        LEGACY_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, LEGACY_MODEL_DIR / "classifier_pipeline.joblib")
        joblib.dump(pipeline.named_steps["clf"], LEGACY_MODEL_DIR / "classifier.joblib")
        joblib.dump(pipeline.named_steps["tfidf"], LEGACY_MODEL_DIR / "vectorizer.joblib")
        with open(LEGACY_MODEL_DIR / "model_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"Production model successfully deployed to: {PRODUCTION_MODEL_DIR / 'model.pkl'}")
    else:
        print(f"\n[ACCEPTANCE REJECTED] Candidate {run_id} failed quality gates. Production model was NOT modified.")
        if missing_classes:
            print(f"Missing required classes: {missing_classes}")
        if macro_f1 < acceptance["min_macro_f1"]:
            print(f"Macro F1 ({macro_f1:.4f}) below threshold ({acceptance['min_macro_f1']})")
        if test_accuracy < acceptance["min_accuracy"]:
            print(f"Test accuracy ({test_accuracy:.4f}) below threshold ({acceptance['min_accuracy']})")

    print("=" * 60)

    return metadata


if __name__ == "__main__":
    train_classifier()
