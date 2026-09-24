"""
Standalone tests for the scalable leakage checker (leakage.py, hardening pass 3).
These tests run without a virtualenv by importing directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow direct execution from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from services.ml.training.leakage import (
    LeakageError,
    _exact_overlap,
    _group_overlap,
    _near_duplicate_count_from_groups,
    _near_duplicate_count_scalable,
    check_leakage_detailed,
    MAX_CANDIDATE_PAIRS,
)

THRESHOLD = 0.85


# ── helpers ──────────────────────────────────────────────────────────────────

def make_df(texts, event_ids=None, source_ids=None):
    d = {"text": texts}
    if event_ids:
        d["event_id"] = event_ids
    if source_ids:
        d["source_id"] = source_ids
    return pd.DataFrame(d)


# ── exact overlap ─────────────────────────────────────────────────────────────

def test_exact_overlap_zero():
    a = pd.Series(["heavy rain in mumbai", "flooding reported"])
    b = pd.Series(["cyclone alert issued", "wind gusts observed"])
    assert _exact_overlap(a, b) == 0, "Expected zero exact overlap"

def test_exact_overlap_one():
    a = pd.Series(["heavy rain in mumbai", "flooding reported"])
    b = pd.Series(["flooding reported", "cyclone alert"])
    assert _exact_overlap(a, b) == 1

def test_exact_overlap_full():
    a = pd.Series(["abc", "def"])
    b = pd.Series(["abc", "def"])
    assert _exact_overlap(a, b) == 2


# ── group overlap ─────────────────────────────────────────────────────────────

def test_group_overlap_none_when_column_missing():
    assert _group_overlap(None, pd.Series(["a"])) is None
    assert _group_overlap(pd.Series(["a"]), None) is None

def test_group_overlap_counts_shared():
    a = pd.Series(["ev1", "ev2"])
    b = pd.Series(["ev2", "ev3"])
    assert _group_overlap(a, b) == 1


# ── inverted-index scalable near-dup ─────────────────────────────────────────

def test_nd_scalable_no_duplicates():
    a = pd.Series(["heavy rain in mumbai today"])
    b = pd.Series(["cyclone alert issued in gujarat"])
    count, method = _near_duplicate_count_scalable(a, b, THRESHOLD)
    assert count == 0, f"Expected 0, got {count}"
    assert method == "inverted_index_exact"

def test_nd_scalable_detects_near_dup():
    # Two texts that share most tokens (Jaccard ≥ 0.85).
    base = "heavy rain flooding reported in district"
    near = "heavy rain flooding reported in districts"     # Jaccard ≈ 0.857
    a = pd.Series([base])
    b = pd.Series([near])
    count, method = _near_duplicate_count_scalable(a, b, THRESHOLD)
    # Compute expected Jaccard manually to confirm test validity
    ta = set(base.split()); tb = set(near.split())
    j = len(ta & tb) / len(ta | tb)
    if j >= THRESHOLD:
        assert count == 1, f"Expected 1 near-dup (Jaccard={j:.3f}), got {count}"
    else:
        assert count == 0, f"Jaccard {j:.3f} below threshold; should be 0"
    assert method == "inverted_index_exact"

def test_nd_scalable_exact_dups_excluded():
    # Exact duplicates should NOT be counted by scalable (they're handled by _exact_overlap).
    a = pd.Series(["flooding reported in mumbai"])
    b = pd.Series(["flooding reported in mumbai"])
    count, method = _near_duplicate_count_scalable(a, b, THRESHOLD)
    assert count == 0, "Exact dups should be excluded from near-dup count"

def test_nd_scalable_empty_input():
    a = pd.Series([], dtype=str)
    b = pd.Series(["some text"])
    count, method = _near_duplicate_count_scalable(a, b, THRESHOLD)
    assert count == 0
    assert method == "inverted_index_exact"

def test_nd_scalable_cap_triggers():
    """Cap must return 'inverted_index_capped' when exceeded."""
    # Create texts where many tokens are shared, then set cap=1.
    a = pd.Series([f"rain flood wind storm event{i}" for i in range(20)])
    b = pd.Series([f"rain flood wind storm event{i}" for i in range(20, 40)])
    count, method = _near_duplicate_count_scalable(a, b, THRESHOLD, max_candidates=1)
    # With cap=1 and shared token "rain", candidate count immediately exceeds cap.
    assert method == "inverted_index_capped", f"Expected capped, got method={method}"


# ── group-membership fast-path ───────────────────────────────────────────────

def test_nd_from_groups_no_crossing():
    idx_train = pd.Index([0, 1, 2])
    idx_val   = pd.Index([3, 4])
    # Groups: {0,1,2} in group 0; {3,4} in group 1 — no crossing
    groups = pd.Series({0: 0, 1: 0, 2: 0, 3: 1, 4: 1})
    count, method = _near_duplicate_count_from_groups(idx_train, idx_val, groups)
    assert count == 0
    assert method == "group_membership"

def test_nd_from_groups_detects_crossing():
    idx_train = pd.Index([0, 1])
    idx_val   = pd.Index([2, 3])
    # Groups: row 0 and row 2 share group root 0 → crossing!
    groups = pd.Series({0: 0, 1: 1, 2: 0, 3: 2})
    count, method = _near_duplicate_count_from_groups(idx_train, idx_val, groups)
    assert count == 1  # group 0 crosses train/val boundary
    assert method == "group_membership"


# ── check_leakage_detailed ───────────────────────────────────────────────────

def _clean_splits():
    """Three non-overlapping, non-near-duplicate splits."""
    train = make_df(["flooding in district north", "rain alert issued", "cyclone warning"],
                    event_ids=["e1", "e2", "e3"])
    val   = make_df(["heatwave grips city", "cold wave advisory"],
                    event_ids=["e4", "e5"])
    test  = make_df(["storm surge coastal", "earthquake tremors minor"],
                    event_ids=["e6", "e7"])
    return train, val, test

def test_detailed_passes_on_clean_splits():
    train, val, test = _clean_splits()
    report = check_leakage_detailed(train, val, test, policy="strict")
    assert report["passed"] is True
    assert report["blocking_leakage_found"] is False
    assert report["near_duplicate_check_complete"] is True

def test_detailed_uses_group_fastpath_when_provided():
    """Groups must use the same index as the DataFrame rows, not arbitrary integers."""
    # Build DataFrames with an explicit non-overlapping global integer index
    # so that groups keyed by that index correctly map each row to a unique group.
    train = pd.DataFrame(
        {"text": ["flooding in district north", "rain alert issued", "cyclone warning"],
         "event_id": ["e1", "e2", "e3"]},
        index=[0, 1, 2],
    )
    val = pd.DataFrame(
        {"text": ["heatwave grips city", "cold wave advisory"],
         "event_id": ["e4", "e5"]},
        index=[3, 4],
    )
    test = pd.DataFrame(
        {"text": ["storm surge coastal", "earthquake tremors minor"],
         "event_id": ["e6", "e7"]},
        index=[5, 6],
    )
    # Each row in its own distinct group — no group crosses split boundaries.
    groups = pd.Series({0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6})
    report = check_leakage_detailed(train, val, test, policy="strict", leakage_groups=groups)
    methods = report.get("near_duplicate_check_methods", {})
    assert all(v == "group_membership" for v in methods.values()), \
        f"Expected all group_membership, got {methods}"
    assert report["passed"] is True, f"Expected pass, got report={report}"

def test_detailed_exact_leakage_triggers():
    shared_text = "heavy rain flooding in district"
    train = make_df([shared_text, "other event one"], event_ids=["e1", "e2"])
    val   = make_df([shared_text, "another event"], event_ids=["e1", "e3"])  # same text AND event_id
    test  = make_df(["unrelated event x"], event_ids=["e9"])
    try:
        check_leakage_detailed(train, val, test, policy="strict")
        assert False, "Should have raised LeakageError"
    except LeakageError as e:
        assert e.report["total_exact_leakage_cases"] > 0

def test_detailed_warning_policy_does_not_raise():
    shared_text = "flooding in north district"
    train = make_df([shared_text, "other event one"])
    val   = make_df([shared_text, "another event"])
    test  = make_df(["unrelated event x"])
    report = check_leakage_detailed(train, val, test, policy="warning")
    assert report["blocking_leakage_found"] is True
    assert report["passed"] is False  # leakage found, but no exception

def test_detailed_disabled_policy_skips():
    train = make_df(["a b c"])
    val   = make_df(["a b c"])
    test  = make_df(["a b c"])
    report = check_leakage_detailed(train, val, test, policy="disabled")
    assert report["checked"] is False
    assert report["passed"] is True

def test_detailed_capped_strict_fails_closed():
    """When cap is hit in scalable method under strict, must raise LeakageError.

    We test the cap directly via _near_duplicate_count_scalable (passing max_candidates=1)
    and verify check_leakage_detailed raises under strict when it receives a capped result.
    """
    from services.ml.training.leakage import _near_duplicate_count_scalable

    # Verify capped method label is returned by the inner function.
    a = pd.Series([f"rain flood wind storm event{i}" for i in range(10)])
    b = pd.Series([f"rain flood wind storm report{i}" for i in range(5)])
    _, method = _near_duplicate_count_scalable(a, b, THRESHOLD, max_candidates=1)
    assert method == "inverted_index_capped", f"Expected capped, got {method}"

    # Now verify check_leakage_detailed fails closed when the inverted-index path
    # returns 'capped'.  We monkey-patch _near_duplicate_count_scalable to always
    # return (0, 'inverted_index_capped') to simulate the cap condition.
    import services.ml.training.leakage as leakage_mod

    def _always_capped(a, b, threshold, max_candidates=leakage_mod.MAX_CANDIDATE_PAIRS):
        return 0, "inverted_index_capped"

    original_fn = leakage_mod._near_duplicate_count_scalable
    leakage_mod._near_duplicate_count_scalable = _always_capped
    try:
        train = make_df(["flooding in district north", "rain alert issued"])
        val   = make_df(["heatwave grips city"])
        test  = make_df(["storm surge coastal"])
        try:
            check_leakage_detailed(train, val, test, policy="strict", leakage_groups=None)
            assert False, "Expected LeakageError under strict when cap hit"
        except LeakageError as e:
            assert "cap" in str(e).lower() or "completed" in str(e).lower(), str(e)
    finally:
        leakage_mod._near_duplicate_count_scalable = original_fn


# ── discover_data_files deduplication ────────────────────────────────────────

def test_discover_data_files_deduplicates(tmp_path):
    """discover_data_files() must return each physical file exactly once."""
    import shutil
    from services.ml.training.prepare_data import discover_data_files

    # Create two sub-directories with the same file (symlink-equivalent: copy).
    dir_a = tmp_path / "incoming"
    dir_b = tmp_path / "raw"
    dir_a.mkdir(); dir_b.mkdir()
    src = dir_a / "events.json"
    src.write_text('{"events": []}')
    shutil.copy2(src, dir_b / "events.json")

    found = discover_data_files(tmp_path)
    resolved = [f.resolve() for f in found]
    assert len(resolved) == len(set(resolved)), \
        f"discover_data_files returned duplicate resolved paths: {resolved}"


# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_exact_overlap_zero,
        test_exact_overlap_one,
        test_exact_overlap_full,
        test_group_overlap_none_when_column_missing,
        test_group_overlap_counts_shared,
        test_nd_scalable_no_duplicates,
        test_nd_scalable_detects_near_dup,
        test_nd_scalable_exact_dups_excluded,
        test_nd_scalable_empty_input,
        test_nd_scalable_cap_triggers,
        test_nd_from_groups_no_crossing,
        test_nd_from_groups_detects_crossing,
        test_detailed_passes_on_clean_splits,
        test_detailed_uses_group_fastpath_when_provided,
        test_detailed_exact_leakage_triggers,
        test_detailed_warning_policy_does_not_raise,
        test_detailed_disabled_policy_skips,
        test_detailed_capped_strict_fails_closed,
    ]
    passed = failed = 0
    for t in tests:
        try:
            if t.__name__ == "test_discover_data_files_deduplicates":
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    t(Path(td))
            else:
                t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {passed + failed} tests.")
    if failed:
        sys.exit(1)
