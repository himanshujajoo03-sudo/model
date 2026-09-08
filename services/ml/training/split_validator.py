from __future__ import annotations

"""
Train/Validation/Test Split Feasibility Validator (hardening pass 2, Rule 2).

The previous implementation only checked `count >= min_samples_per_class` (a
fixed constant, e.g. 3), which does NOT guarantee that stratified splitting
into train/val/test will actually succeed or produce a meaningful split. A
class with 3 samples split 80/10/10 will almost certainly end up with 0
samples in validation or test.

This module computes, from the CONFIGURED split ratios, the minimum number
of samples a class needs so that stratified splitting can place at least one
representative of that class into every split.

Mathematical basis:
    For a class with `count` samples to be guaranteed at least one member in
    every split of relative size r_i (train/val/test ratios, r_i in (0, 1),
    sum(r_i) == 1), it is REQUIRED that:

        count * min(r_train, r_val, r_test) >= 1

    i.e.

        count >= ceil(1 / min(r_train, r_val, r_test))

    This is a NECESSARY condition derived directly from proportional
    stratified allocation; sklearn's `train_test_split(..., stratify=y)`
    cannot place a member of a class into a split whose proportional share
    of that class rounds to zero. We treat it as the hard minimum bound.
    (Sklearn may occasionally succeed with slightly fewer samples due to
    internal rounding behavior, but never guarantees success below this
    bound, so we do not rely on that.)
"""

import math
from typing import Any


class SplitFeasibilityError(ValueError):
    """Raised when the dataset cannot be safely split into train/val/test
    while preserving stratification across every class."""

    def __init__(self, message: str, report: dict[str, Any] | None = None):
        super().__init__(message)
        self.report = report or {}


def minimum_samples_per_class(split_ratios: dict[str, float]) -> int:
    """
    Compute the minimum number of samples a class needs so stratified
    splitting can place at least one sample of that class into each of
    train/val/test, given the configured ratios.
    """
    required_keys = {"train", "val", "test"}
    if set(split_ratios.keys()) != required_keys:
        raise ValueError(
            f"split_ratios must contain exactly {sorted(required_keys)}, got {sorted(split_ratios.keys())}"
        )

    ratios = [float(split_ratios[k]) for k in required_keys]
    min_ratio = min(ratios)
    if min_ratio <= 0.0:
        raise ValueError("All split ratios must be > 0 to compute minimum samples per class.")

    # At least 2 is always required (a class must be splittable at all).
    return max(2, math.ceil(1.0 / min_ratio))


def validate_split_feasibility(
    class_counts: dict[str, int],
    split_ratios: dict[str, float],
) -> dict[str, Any]:
    """
    Verify that every class has enough samples to survive stratified
    train/val/test splitting under the configured ratios.

    Returns a feasibility report dict on success.
    Raises SplitFeasibilityError with a detailed, actionable report on failure.
    """
    required = minimum_samples_per_class(split_ratios)
    total = sum(class_counts.values())

    problems: dict[str, dict[str, int]] = {}
    for cat, count in class_counts.items():
        if count < required:
            problems[cat] = {
                "current_count": count,
                "required_count": required,
                "additional_needed": required - count,
            }

    report = {
        "total_records": total,
        "class_distribution": dict(class_counts),
        "split_ratios": dict(split_ratios),
        "min_required_per_class": required,
        "problematic_classes": problems,
        "feasible": not problems,
    }

    if problems:
        lines = [
            f"Dataset cannot be safely split into train/val/test "
            f"({split_ratios['train']:.0%}/{split_ratios['val']:.0%}/{split_ratios['test']:.0%}).",
            f"Total dataset size: {total} records across {len(class_counts)} classes.",
            f"Minimum samples required per class for these ratios: {required}.",
            "Problematic classes:",
        ]
        for cat, info in sorted(problems.items()):
            lines.append(
                f"  - '{cat}': has {info['current_count']}, needs {info['required_count']} "
                f"(add {info['additional_needed']} more example(s))"
            )
        lines.append(f"Full class distribution: {class_counts}")

        raise SplitFeasibilityError("\n".join(lines), report=report)

    return report
