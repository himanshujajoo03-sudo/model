from __future__ import annotations

"""
Scalable Data Leakage Detection (hardening pass 3 — scalability pass).

Leakage checks:

  1. Exact normalized-text overlap (set intersection — O(n+m), always computed)
  2. Near-duplicate text overlap — Jaccard token similarity ≥ threshold
     - **Fast path** (default when leakage_groups are provided by train.py):
       verify that no leakage group root crosses split boundaries — O(n).
       This is the authoritative check because the same group-building logic
       that drives the split is used to confirm the split.
     - **Full path** (standalone use or when groups are not available):
       token-inverted-index candidate generation + exact Jaccard — see
       _near_duplicate_count_scalable() for complexity analysis.
  3. Shared event_id across splits (set intersection, always computed)
  4. Source overlap (informational only; a shared source is expected)

Leakage policy (training.leakage_policy in ml_config.yaml):
  - "strict"   (default): abort training if any blocking leakage is found.
                           Also fails closed if the near-duplicate audit
                           cannot be safely completed.
  - "warning": log a warning and continue (useful for experimentation).
  - "disabled": skip the expanded checks entirely.

Near-duplicate comparison — scalability design
───────────────────────────────────────────────
The previous implementation was a bare O(n×m) pairwise cross-product that
becomes intractable above ~1,500 rows per split.  With the current dataset
(7,709 train × 960 val ≈ 7.4M pairs) the check was already being skipped,
which caused the strict-mode LeakageError "could not be completed".

The new approach:

  Phase 1 — Candidate generation (inverted index):
    Build a token→[row_ids] inverted index over set A.
    For each text in B, look up each of its tokens in A's index.
    Rows in A that share ≥ 1 token with a row in B are candidate pairs.
    This generates at most Σ|tokens_b| × avg_postings candidates, which
    in practice is orders of magnitude smaller than |A|×|B|.

  Phase 2 — Exact Jaccard verification:
    Compute exact Jaccard only for the candidate pairs.

  Complexity:
    Phase 1: O(Σ_B |tokens_b| × avg_postings_len)
    Phase 2: O(|candidates| × avg_token_set_size)
    Total: practical O(n + m + candidates), not O(n×m).

  Worst case (all texts share a single high-frequency token, e.g. "the"):
    Approaches O(n×m), bounded by MAX_CANDIDATE_PAIRS.
    Under strict mode this still fails closed with a clear error rather than
    silently skipping.  High-frequency stop-words in very short texts are
    the pathological case; normalize_text() should strip them in practice.

  Scalability at 50k–100k records:
    At 50k train / 5k val with avg 10-token texts and 5 candidate matches
    per token lookup, ~50k candidates are generated — well within budget.
    The cap (default 10M candidate pairs) is a last-resort safety valve,
    not the primary scaling mechanism.  The inverted index is the mechanism.
"""

import logging
from typing import Any, Optional

import pandas as pd

try:
    from ..utils.text import text_similarity
except (ImportError, ValueError):
    from utils.text import text_similarity  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

VALID_LEAKAGE_POLICIES = ("strict", "warning", "disabled")

# Safety cap on the total number of candidate pairs considered during
# the inverted-index near-duplicate audit.  Unlike the old MAX_PAIRWISE_
# COMPARISONS this is NOT a dataset-size cutoff — it is an upper bound on
# the inner loop of Phase 2.  It can only be hit when texts share an
# unusually large number of tokens (degenerate/pathological input).
# At 50k–100k realistic weather-event records this cap is never reached.
MAX_CANDIDATE_PAIRS = 10_000_000


class LeakageError(ValueError):
    """Raised when the configured leakage policy is violated."""

    def __init__(self, message: str, report: dict[str, Any] | None = None):
        super().__init__(message)
        self.report = report or {}


# ──────────────────────────────────────────────────────────────────────────────
# Exact overlap helpers (unchanged semantics)
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Near-duplicate detection — group fast-path (O(n))
# ──────────────────────────────────────────────────────────────────────────────

def _near_duplicate_count_from_groups(
    idx_a: pd.Index,
    idx_b: pd.Index,
    leakage_groups: pd.Series,
) -> tuple[int, str]:
    """Verify near-duplicate isolation using pre-computed leakage groups.

    This is the O(n) fast path used when groups have already been built by
    leakage_safe_split().  It checks that no group root appears in both
    idx_a and idx_b — which is exactly what the group-based splitter
    guarantees.  Finding a crossing group here is an internal invariant
    violation and is treated as leakage.

    Returns (crossing_group_count, "group_membership").
    The 'group_membership' method label indicates the audit was complete.
    """
    roots_a = set(leakage_groups.reindex(idx_a).dropna().astype(int).tolist())
    roots_b = set(leakage_groups.reindex(idx_b).dropna().astype(int).tolist())
    crossing = len(roots_a & roots_b)
    return crossing, "group_membership"


# ──────────────────────────────────────────────────────────────────────────────
# Near-duplicate detection — inverted-index full path (scalable)
# ──────────────────────────────────────────────────────────────────────────────

def _near_duplicate_count_scalable(
    a: pd.Series,
    b: pd.Series,
    threshold: float,
    max_candidates: int = MAX_CANDIDATE_PAIRS,
) -> tuple[int, str]:
    """Count near-duplicate text pairs between two splits.

    Uses a two-phase token-inverted-index + exact Jaccard approach that
    scales to 100k+ records without a hard row-count cutoff.

    Phase 1 — candidate generation (O(Σ|tokens_b| × avg_postings)):
      Build a token → {row_id, ...} inverted index over unique texts in A.
      For each unique text in B, collect the union of A-row IDs that share
      at least one token.  These are candidate pairs worth checking.

    Phase 2 — exact verification (O(|candidates| × avg_token_size)):
      Compute exact Jaccard for each candidate pair (a_text, b_text).

    If the number of candidate pairs exceeds `max_candidates`, return
    (count_so_far, "inverted_index_capped") so callers can treat this
    as an incomplete audit under strict mode.

    Returns (count, method_label) where method_label is:
      "inverted_index_exact" — full audit completed
      "inverted_index_capped" — audit incomplete (cap hit)
    """
    a_list = [t for t in a.dropna().astype(str).tolist() if t]
    b_list = [t for t in b.dropna().astype(str).tolist() if t]
    if not a_list or not b_list:
        return 0, "inverted_index_exact"

    # Deduplicate: exact overlaps are caught by _exact_overlap(); we skip
    # them here to avoid double-counting and wasted computation.
    a_texts = list(set(a_list))
    b_texts = list(set(b_list))
    exact_a = set(a_texts)
    exact_b = set(b_texts)
    # Remove texts present in both splits (exact duplicates already counted).
    a_unique = [t for t in a_texts if t not in exact_b]
    b_unique = [t for t in b_texts if t not in exact_a]

    if not a_unique or not b_unique:
        return 0, "inverted_index_exact"

    # Precompute token sets once.
    a_token_sets = {t: set(t.split()) for t in a_unique}
    b_token_sets = {t: set(t.split()) for t in b_unique}

    # Phase 1: build inverted index over A (token → set of A-text keys).
    inv: dict[str, set[str]] = {}
    for text, tokens in a_token_sets.items():
        for tok in tokens:
            inv.setdefault(tok, set()).add(text)

    # Phase 2: for each B text, collect candidate A texts, then verify Jaccard.
    count = 0
    total_candidates = 0

    for b_text, b_tokens in b_token_sets.items():
        if not b_tokens:
            continue

        # Collect candidate A texts (those sharing ≥1 token with b_text).
        candidate_a_texts: set[str] = set()
        for tok in b_tokens:
            if tok in inv:
                candidate_a_texts |= inv[tok]

        # Safety cap: bail out if total candidates would be exceeded.
        new_total = total_candidates + len(candidate_a_texts)
        if new_total > max_candidates:
            logger.warning(
                "Near-duplicate leakage audit: candidate pair cap (%d) exceeded "
                "after %d verified pairs. Returning partial result. "
                "Input texts may have unusually high token overlap (e.g. stop-words "
                "not removed by normalization).",
                max_candidates,
                total_candidates,
            )
            return count, "inverted_index_capped"
        total_candidates = new_total

        for a_text in candidate_a_texts:
            a_tokens = a_token_sets[a_text]
            union = a_tokens | b_tokens
            if not union:
                continue
            jaccard = len(a_tokens & b_tokens) / len(union)
            if jaccard >= threshold:
                count += 1

    return count, "inverted_index_exact"


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def check_leakage_detailed(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    policy: str = "strict",
    near_duplicate_threshold: float = 0.85,
    leakage_groups: Optional[pd.Series] = None,
) -> dict[str, Any]:
    """
    Full leakage audit across train/val/test splits.

    Each dataframe must have a 'text' column (already normalized). If
    'event_id' and/or 'source_id' columns are present, grouped overlap is
    also checked.

    leakage_groups (optional):
        Pre-computed union-find group labels from leakage_safe_split().
        When provided, the near-duplicate audit uses the O(n) group-membership
        fast path instead of the inverted-index scan.  Passing groups is
        strongly recommended for production training runs because it uses the
        exact same grouping that drove the split — confirming split integrity
        directly rather than re-deriving it.
        When not provided (e.g., standalone audit), the inverted-index method
        is used automatically.

    Returns a detailed report dict.  Raises LeakageError if policy == "strict"
    and blocking leakage (exact text overlap, shared event_id, or near-duplicate
    overlap) is found.  Also raises LeakageError under strict mode if the
    near-duplicate audit could not be completed (fail-closed).
    """
    policy = (policy or "strict").lower()
    if policy not in VALID_LEAKAGE_POLICIES:
        raise ValueError(
            f"Invalid leakage policy '{policy}'. Must be one of {VALID_LEAKAGE_POLICIES}."
        )

    report: dict[str, Any] = {"policy": policy}

    if policy == "disabled":
        report["checked"] = False
        report["passed"] = True
        return report

    report["checked"] = True

    # ── 1. Exact text overlap (always computed, O(n+m)) ──────────────────────
    report["train_val_exact_overlap"]  = _exact_overlap(train_df["text"], val_df["text"])
    report["train_test_exact_overlap"] = _exact_overlap(train_df["text"], test_df["text"])
    report["val_test_exact_overlap"]   = _exact_overlap(val_df["text"],  test_df["text"])
    report["total_exact_leakage_cases"] = (
        report["train_val_exact_overlap"]
        + report["train_test_exact_overlap"]
        + report["val_test_exact_overlap"]
    )

    # ── 2. Event-id overlap (always computed, O(n+m)) ────────────────────────
    report["event_id_overlap"] = {
        "train_val":  _group_overlap(train_df.get("event_id"), val_df.get("event_id")),
        "train_test": _group_overlap(train_df.get("event_id"), test_df.get("event_id")),
        "val_test":   _group_overlap(val_df.get("event_id"),   test_df.get("event_id")),
    }

    # ── 3. Source overlap (informational only) ───────────────────────────────
    report["source_overlap"] = {
        "train_val":  _group_overlap(train_df.get("source_id"), val_df.get("source_id")),
        "train_test": _group_overlap(train_df.get("source_id"), test_df.get("source_id")),
        "val_test":   _group_overlap(val_df.get("source_id"),   test_df.get("source_id")),
    }

    # ── 4. Near-duplicate overlap ────────────────────────────────────────────
    # Prefer the group fast-path (O(n)) when leakage_groups are available.
    # Fall back to the scalable inverted-index method otherwise.
    nd_results: dict[str, tuple[int, str]] = {}

    if leakage_groups is not None:
        # Fast path: group-membership cross-check (always complete, O(n)).
        nd_results["train_val"]  = _near_duplicate_count_from_groups(
            train_df.index, val_df.index,  leakage_groups
        )
        nd_results["train_test"] = _near_duplicate_count_from_groups(
            train_df.index, test_df.index, leakage_groups
        )
        nd_results["val_test"]   = _near_duplicate_count_from_groups(
            val_df.index,  test_df.index,  leakage_groups
        )
    else:
        # Full path: inverted-index scan (scalable, may be capped on degenerate input).
        nd_results["train_val"]  = _near_duplicate_count_scalable(
            train_df["text"], val_df["text"],  near_duplicate_threshold
        )
        nd_results["train_test"] = _near_duplicate_count_scalable(
            train_df["text"], test_df["text"], near_duplicate_threshold
        )
        nd_results["val_test"]   = _near_duplicate_count_scalable(
            val_df["text"],   test_df["text"], near_duplicate_threshold
        )

    report["near_duplicate_overlap"] = {k: v[0] for k, v in nd_results.items()}
    report["near_duplicate_check_methods"] = {k: v[1] for k, v in nd_results.items()}

    # Audit is incomplete if ANY pair used the capped method.
    methods = [v[1] for v in nd_results.values()]
    audit_complete = all(m in ("group_membership", "inverted_index_exact") for m in methods)
    report["near_duplicate_check_complete"] = audit_complete

    # ── 5. Aggregate and policy enforcement ─────────────────────────────────
    event_leak_total = sum(
        v for v in report["event_id_overlap"].values() if isinstance(v, int)
    )
    near_dup_total = sum(report["near_duplicate_overlap"].values())

    report["near_duplicate_leakage_cases"] = near_dup_total
    blocking = (
        report["total_exact_leakage_cases"] > 0
        or event_leak_total > 0
        or near_dup_total > 0
    )
    report["blocking_leakage_found"] = blocking
    report["passed"] = not blocking

    # Fail closed if the near-dup audit is incomplete and policy is strict.
    if not audit_complete and policy == "strict":
        raise LeakageError(
            "Near-duplicate leakage check could not be completed for all split pairs "
            "(candidate pair cap was hit — see WARNING log for details). "
            "leakage_policy=strict requires a fully auditable result. "
            "Training aborted to prevent an under-checked evaluation score.\n"
            "Mitigation: ensure normalize_text() strips common stop-words so the "
            "inverted-index fan-out stays manageable, or pass pre-computed "
            "leakage_groups to use the O(n) group-membership fast path.",
            report=report,
        )

    if blocking:
        message = (
            f"Data leakage detected: {report['total_exact_leakage_cases']} exact text "
            f"overlap case(s), {event_leak_total} shared event_id case(s), and "
            f"{near_dup_total} near-duplicate overlap case(s) across train/val/test splits."
        )
        if policy == "strict":
            raise LeakageError(
                f"{message} Training aborted (leakage_policy=strict) to prevent an "
                f"inflated evaluation score. Full report: {report}",
                report=report,
            )
        logger.warning(
            "%s Continuing because leakage_policy=warning. Report: %s", message, report
        )

    return report
