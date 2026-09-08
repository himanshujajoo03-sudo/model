from __future__ import annotations

"""
Centralized Configuration Loader and Validator.
Ensures single source of truth from config/ml_config.yaml with startup validation.
"""

from pathlib import Path
import math
from typing import Any
import yaml

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CONFIG_DIR / "ml_config.yaml"

_LOADED_CONFIG: dict[str, Any] | None = None


class ConfigurationError(ValueError):
    """Raised when configuration values are invalid or violate schema constraints."""
    pass


def validate_weights(weights: dict[str, Any], name: str, expected_sum: float = 1.0, tolerance: float = 1e-4) -> dict[str, float]:
    """Validate that weights are numeric, non-negative, and sum to expected_sum."""
    if not isinstance(weights, dict) or not weights:
        raise ConfigurationError(f"{name} weights must be a non-empty dictionary.")

    clean_weights = {}
    for k, v in weights.items():
        if not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v):
            raise ConfigurationError(f"Weight '{k}' in {name} must be a valid number, got {v}")
        if v < 0.0:
            raise ConfigurationError(f"Weight '{k}' in {name} must be non-negative, got {v}")
        clean_weights[k] = float(v)

    total = sum(clean_weights.values())
    if abs(total - expected_sum) > tolerance:
        raise ConfigurationError(
            f"Weights in {name} must sum to {expected_sum:.2f}, but got {total:.4f}. "
            f"Weights: {clean_weights}"
        )

    return clean_weights


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Perform strict validation of loaded configuration."""
    # 1. Credibility weights
    cred = config.get("credibility", {})
    cred_weights = cred.get("weights", {})
    required_cred_keys = {
        "source_trust", "corroboration", "weather_agreement",
        "temporal_consistency", "spatial_consistency", "content_quality"
    }
    missing_cred = required_cred_keys - set(cred_weights.keys())
    if missing_cred:
        raise ConfigurationError(f"Missing required credibility weights: {missing_cred}")
    validate_weights(cred_weights, "credibility")

    # 0. Classification thresholds
    classification = config.get("classification", {})
    tier = classification.get("confidence_tiers", {})
    for key, default in (("high", 0.80), ("medium", 0.60), ("low", 0.40)):
        v = tier.get(key, default)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)) or not 0.0 <= float(v) <= 1.0:
            raise ConfigurationError(f"classification.confidence_tiers['{key}'] must be within [0, 1], got {v!r}.")
    if not (float(tier.get("low", 0.40)) <= float(tier.get("medium", 0.60)) <= float(tier.get("high", 0.80))):
        raise ConfigurationError("classification.confidence_tiers must satisfy low <= medium <= high.")
    model_threshold = classification.get("model_confidence_threshold", 0.75)
    if not isinstance(model_threshold, (int, float)) or isinstance(model_threshold, bool) or not math.isfinite(float(model_threshold)) or not 0.0 <= float(model_threshold) <= 1.0:
        raise ConfigurationError(f"classification.model_confidence_threshold must be within [0, 1], got {model_threshold!r}.")

    # 2. Duplicate weights and thresholds
    dup = config.get("duplicate", {})
    dup_weights = dup.get("weights", {})
    required_dup_keys = {"text", "source_id", "source_url", "category", "time", "distance"}
    missing_dup = required_dup_keys - set(dup_weights.keys())
    if missing_dup:
        raise ConfigurationError(f"Missing required duplicate weights: {missing_dup}")
    validate_weights(dup_weights, "duplicate")

    prob_thresh = dup.get("probable_threshold", 0.85)
    poss_thresh = dup.get("possible_threshold", 0.60)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) for v in (poss_thresh, prob_thresh)):
        raise ConfigurationError("duplicate thresholds must be finite numeric values.")
    if not (0.0 <= poss_thresh <= prob_thresh <= 1.0):
        raise ConfigurationError(
            f"Duplicate thresholds invalid: expected 0 <= possible ({poss_thresh}) <= probable ({prob_thresh}) <= 1"
        )

    # 3. Clustering parameters
    clustering = config.get("clustering", {})
    if clustering.get("radius_km", 3.0) <= 0:
        raise ConfigurationError("clustering.radius_km must be > 0")
    if clustering.get("time_window_minutes", 30.0) <= 0:
        raise ConfigurationError("clustering.time_window_minutes must be > 0")
    if clustering.get("max_cluster_size", 50) <= 0:
        raise ConfigurationError("clustering.max_cluster_size must be > 0")

    # 4. Training split ratios
    training = config.get("training", {})
    splits = training.get("split_ratios", {"train": 0.80, "val": 0.10, "test": 0.10})

    required_split_keys = {"train", "val", "test"}
    actual_split_keys = set(splits.keys())
    if actual_split_keys != required_split_keys:
        missing = required_split_keys - actual_split_keys
        extra = actual_split_keys - required_split_keys
        problems = []
        if missing:
            problems.append(f"missing keys: {sorted(missing)}")
        if extra:
            problems.append(f"unexpected extra keys: {sorted(extra)}")
        raise ConfigurationError(
            f"training.split_ratios must contain EXACTLY {sorted(required_split_keys)}; {'; '.join(problems)}."
        )
    for key in required_split_keys:
        v = splits[key]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0.0:
            raise ConfigurationError(
                f"training.split_ratios['{key}'] must be a positive number, got {v!r}."
            )
    validate_weights(splits, "training.split_ratios", expected_sum=1.0)

    # 5. Minimum samples per class must be a positive integer
    min_samples = training.get("min_samples_per_class", 3)
    if not isinstance(min_samples, int) or isinstance(min_samples, bool) or min_samples < 1:
        raise ConfigurationError(
            f"training.min_samples_per_class must be a positive integer, got {min_samples!r}."
        )

    # 6. Leakage policy must be one of the supported values
    leakage_policy = training.get("leakage_policy", "strict")
    if leakage_policy not in ("strict", "warning", "disabled"):
        raise ConfigurationError(
            f"training.leakage_policy must be one of 'strict', 'warning', 'disabled'; got {leakage_policy!r}."
        )

    # 7. Acceptance thresholds must be valid probabilities
    acceptance = training.get("acceptance_thresholds", {})
    for key, v in acceptance.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.0 <= v <= 1.0):
            raise ConfigurationError(
                f"training.acceptance_thresholds['{key}'] must be within [0, 1], got {v!r}."
            )

    near_dup = training.get("near_duplicate_threshold", 0.85)
    if not isinstance(near_dup, (int, float)) or isinstance(near_dup, bool) or not math.isfinite(float(near_dup)) or not 0.0 <= float(near_dup) <= 1.0:
        raise ConfigurationError(f"training.near_duplicate_threshold must be within [0, 1], got {near_dup!r}.")

    watcher = training.get("watcher", {})
    for key in ("debounce_seconds", "poll_interval_seconds"):
        v = watcher.get(key, 2.0)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)) or float(v) < 0.0:
            raise ConfigurationError(f"training.watcher.{key} must be a finite non-negative number, got {v!r}.")

    corroboration = config.get("corroboration", {})
    for key in ("radius_km", "window_minutes"):
        v = corroboration.get(key, 10.0 if key == "radius_km" else 30.0)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)) or float(v) <= 0.0:
            raise ConfigurationError(f"corroboration.{key} must be a finite positive number, got {v!r}.")

    max_future = clustering.get("max_future_skew_minutes", 5.0)
    if not isinstance(max_future, (int, float)) or isinstance(max_future, bool) or not math.isfinite(float(max_future)) or float(max_future) < 0.0:
        raise ConfigurationError(f"clustering.max_future_skew_minutes must be finite and >= 0, got {max_future!r}.")

    return config


def load_ml_config(force_reload: bool = False) -> dict[str, Any]:
    """
    Load and validate configuration from ml_config.yaml.
    Caches configuration in-memory unless force_reload is True.
    """
    global _LOADED_CONFIG
    if _LOADED_CONFIG is not None and not force_reload:
        return _LOADED_CONFIG

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    validated = validate_config(raw_config)
    _LOADED_CONFIG = validated
    return _LOADED_CONFIG


def get_config_section(section: str, default: Any = None) -> Any:
    """Convenience function to get a specific section from ml_config."""
    cfg = load_ml_config()
    return cfg.get(section, default)

