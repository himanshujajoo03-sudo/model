from __future__ import annotations

"""
Expanded Data Leakage Detection (hardening pass 2, Rule 3).

The original `check_data_leakage` (kept in training/train.py for backward
compatibility) only detects exact text overlap between splits. This module
adds:

  1. Exact normalized-text overlap (same check, exposed here for reuse)
  2. Near-duplicate text overlap (Jaccard token similarity, configurable
     threshold) — catches paraphrased reports of the same real-world event
  3. Shared event_id across splits — the strongest possible leakage signal;
     if a dataset carries event_id/source metadata, the same real-world
     event must never appear in more than one split
  4. Source overlap — reported for visibility only (a shared source does
     NOT by itself imply leakage; it is expected that a trusted source such
     as a national weather API contributes to every split)

Leakage policy (training.leakage_policy in ml_config.yaml):
  - "strict"   (default, required for production training): abort training
               if exact-text or event_id leakage is found.
  - "warning": log a warning and continue (useful for experimentation).
  - "disabled": skip the expanded checks entirely.

Near-duplicate comparison is O(n * m) between two splits; to avoid runaway
cost on large datasets (§33 perf constraint) it is automatically skipped
above MAX_ROWS_FOR_NEAR_DUPLICATE_CHECK and reported as "not computed".
"""

import logging
from typing import Any, Optional

import pandas as pd

try:
    from ..utils.text import text_similarity
except ImportError:
    from utils.text import text_similarity

logger = logging.getLogger(__name__)

VALID_LEAKAGE_POLICIES = ("strict", "warning", "disabled")

# Guards against O(n*m) near-duplicate comparison blowing up on large datasets.
MAX_PAIRWISE_COMPARISONS = 2_000_000


class LeakageError(ValueError):
    """Raised when the configured leakage policy is violated."""

    def __init__(self, message: str, report: dict[str, Any] | None = None):
        super().__init__(message)
        self.report = report or {}


def _exact_overlap(a: pd.Series, b: pd.Series) -> int:
    return len(set(a.dropna().astype(str)) & set(b.dropna().astype(str)))


def _group_overlap(a: Optional[pd.Series], b: Optional[pd.Series]) -> Optional[int]:
    """Count shared group identifiers (event_id / source_id) between two splits.
    Returns None if the column is unavailable (metadata not tracked for this dataset)."""
    if a is None or b is None:
        return None
    sa = set(a.dropna().astype(str))
    sb = set(b.dropna().astype(str))
    if not sa or not sb:
        return 0
    return len(sa & sb)


def _near_duplicate_count(a: pd.Series, b: pd.Series, threshold: float) -> Optional[int]:
    """Count near-duplicate text pairs between two splits using precomputed token
    sets (Jaccard similarity). Returns None if skipped because the dataset is too
    large for a pairwise comparison."""
    a_list = [t for t in a.dropna().astype(str).tolist() if t]
    b_list = [t for t in b.dropna().astype(str).tolist() if t]
    if not a_list or not b_list:
        return 0
    if len(a_list) * len(b_list) > MAX_PAIRWISE_COMPARISONS:
        logger.warning(
            "Skipping near-duplicate leakage check: %d x %d pairs exceeds safety limit (%d).",
            len(a_list), len(b_list), MAX_PAIRWISE_COMPARISONS
        )
        return None

    # Precompute token sets once (text is already normalized text) instead of
    # re-tokenizing inside the O(n*m) inner loop.
    a_sets = [(t, set(t.split())) for t in set(a_list)]
    b_sets = [(t, set(t.split())) for t in set(b_list)]

    count = 0
    for x_text, x_tokens in a_sets:
        if not x_tokens:
            continue
        for y_text, y_tokens in b_sets:
            if x_text == y_text or not y_tokens:
                continue
            union = x_tokens | y_tokens
            if not union:
                continue
            jaccard = len(x_tokens & y_tokens) / len(union)
            if jaccard >= threshold:
                count += 1
    return count


def check_leakage_detailed(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    policy: str = "strict",
    near_duplicate_threshold: float = 0.85,
) -> dict[str, Any]:
    """
    Full leakage audit across train/val/test splits.

    Each dataframe must have a 'text' column (already normalized). If
    'event_id' and/or 'source_id' columns are present, grouped overlap is
    also checked.

    Returns a detailed report dict. Raises LeakageError if policy == "strict"
    and blocking leakage (exact text overlap or shared event_id) is found.
    """
    policy = (policy or "strict").lower()
    if policy not in VALID_LEAKAGE_POLICIES:
        raise ValueError(f"Invalid leakage policy '{policy}'. Must be one of {VALID_LEAKAGE_POLICIES}.")

    report: dict[str, Any] = {"policy": policy}

    if policy == "disabled":
        report["checked"] = False
        report["passed"] = True
        return report

    report["checked"] = True
    report["train_val_exact_overlap"] = _exact_overlap(train_df["text"], val_df["text"])
    report["train_test_exact_overlap"] = _exact_overlap(train_df["text"], test_df["text"])
    report["val_test_exact_overlap"] = _exact_overlap(val_df["text"], test_df["text"])
    report["total_exact_leakage_cases"] = (
        report["train_val_exact_overlap"]
        + report["train_test_exact_overlap"]
        + report["val_test_exact_overlap"]
    )

    report["event_id_overlap"] = {
        "train_val": _group_overlap(train_df.get("event_id"), val_df.get("event_id")),
        "train_test": _group_overlap(train_df.get("event_id"), test_df.get("event_id")),
        "val_test": _group_overlap(val_df.get("event_id"), test_df.get("event_id")),
    }
    report["source_overlap"] = {
        "train_val": _group_overlap(train_df.get("source_id"), val_df.get("source_id")),
        "train_test": _group_overlap(train_df.get("source_id"), test_df.get("source_id")),
        "val_test": _group_overlap(val_df.get("source_id"), test_df.get("source_id")),
    }
    report["near_duplicate_overlap"] = {
        "train_val": _near_duplicate_count(train_df["text"], val_df["text"], near_duplicate_threshold),
        "train_test": _near_duplicate_count(train_df["text"], test_df["text"], near_duplicate_threshold),
        "val_test": _near_duplicate_count(val_df["text"], test_df["text"], near_duplicate_threshold),
    }

    event_leak_total = sum(v for v in report["event_id_overlap"].values() if isinstance(v, int))
    near_dup_values = [v for v in report["near_duplicate_overlap"].values() if isinstance(v, int)]
    near_duplicate_leak_total = sum(near_dup_values)
    # Near-duplicate overlap is leakage too: strict production checks must not
    # merely report it while allowing training to continue.
    near_duplicate_unknown = any(v is None for v in report["near_duplicate_overlap"].values())
    blocking = (
        report["total_exact_leakage_cases"] > 0
        or event_leak_total > 0
        or near_duplicate_leak_total > 0
    )
    report["near_duplicate_leakage_cases"] = near_duplicate_leak_total
    report["near_duplicate_check_complete"] = not near_duplicate_unknown
    report["blocking_leakage_found"] = blocking
    report["passed"] = not blocking

    if near_duplicate_unknown and policy == "strict":
        raise LeakageError(
            "Near-duplicate leakage check could not be completed for all split pairs under "
            "leakage_policy=strict. Training/evaluation must fail closed instead of assuming "
            "the splits are leakage-free.",
            report=report,
        )

    if blocking:
        message = (
            f"Data leakage detected: {report['total_exact_leakage_cases']} exact text overlap "
            f"case(s), {event_leak_total} shared event_id case(s), and "
            f"{near_duplicate_leak_total} near-duplicate overlap case(s) across train/val/test splits."
        )
        if policy == "strict":
            raise LeakageError(
                f"{message} Training aborted (leakage_policy=strict) to prevent an inflated "
                f"evaluation score. Full report: {report}",
                report=report,
            )
        logger.warning(f"{message} Continuing because leakage_policy=warning. Report: {report}")

    return report
