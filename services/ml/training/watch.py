from __future__ import annotations

"""
Automated Incoming Data File Watcher & Real-Time Retrainer.
Monitors data/incoming/ and data/training/ for new or modified CSV/JSON files,
and automatically triggers the data cleaning and model retraining pipeline.
Monitors data/incoming/, data/training/, and data/raw/ for new or modified CSV/JSON files.
Features:
1. Stabilization debounce (waits for batch file writes to settle before triggering)
2. Single-instance concurrency lock (prevents overlapping retraining runs)
3. Quality-gated atomic deployment (preserves production model on candidate failure)
"""

import sys
import time
import os
import logging
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ..config.config_loader import load_ml_config
    from .train import train_classifier
    from .evaluate import evaluate_models
except ImportError:
    from config.config_loader import load_ml_config
    from training.train import train_classifier
    from training.evaluate import evaluate_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Watcher")

MONITOR_DIRS = [
    PROJECT_ROOT / "data" / "incoming",
    PROJECT_ROOT / "data" / "training",
    PROJECT_ROOT / "data" / "raw",
]

_IS_TRAINING_ACTIVE = False


def get_files_fingerprint(dirs: list[Path]) -> dict[str, float]:
    """Get modification timestamps of all CSV and JSON files in monitored directories."""
    fingerprint = {}
    for d in dirs:
        if d.exists():
            for f in list(d.glob("*.csv")) + list(d.glob("*.json")):
                try:
                    fingerprint[str(f.resolve())] = f.stat().st_mtime
                except OSError:
                    pass
    return fingerprint


def watch_and_retrain(poll_interval_seconds: float | None = None, debounce_seconds: float | None = None):
    """
    Continuously watch incoming data directories with debounced triggering and quality gates.
    When a new or modified file is detected, automatically cleans data, retrains a
    candidate model, and promotes it to production only if it passes acceptance criteria.
    """
    global _IS_TRAINING_ACTIVE
    cfg = load_ml_config()
    watcher_cfg = cfg.get("training", {}).get("watcher", {})

    poll_interval = (
        poll_interval_seconds
        if poll_interval_seconds is not None
        else float(watcher_cfg.get("poll_interval_seconds", 2.0))
    )
    debounce = (
        debounce_seconds
        if debounce_seconds is not None
        else float(watcher_cfg.get("debounce_seconds", 2.0))
    )

    print("=" * 60)
    print("Starting Automated Incoming Data Watcher & Retrainer")
    print(f"Monitoring directories: {[str(d) for d in MONITOR_DIRS]}")
    print(f"Polling interval: {poll_interval}s | Debounce stabilization: {debounce}s")
    print("=" * 60)

    last_fingerprint = get_files_fingerprint(MONITOR_DIRS)
    print(f"Currently tracking {len(last_fingerprint)} file(s). Waiting for incoming data...")

    try:
        while True:
            time.sleep(poll_interval)
            current_fingerprint = get_files_fingerprint(MONITOR_DIRS)

            # Check for new or modified files
            added_files = set(current_fingerprint.keys()) - set(last_fingerprint.keys())
            modified_files = {
                f for f in current_fingerprint
                if f in last_fingerprint and current_fingerprint[f] > last_fingerprint[f]
            }

            if added_files or modified_files:
                if added_files:
                    print(f"\n[NEW FILE DETECTED] {[Path(f).name for f in added_files]}")
                    logger.info(f"New file(s) detected: {[Path(f).name for f in added_files]}")
                if modified_files:
                    print(f"\n[FILE MODIFIED] {[Path(f).name for f in modified_files]}")
                    logger.info(f"File(s) modified: {[Path(f).name for f in modified_files]}")

                print("Triggering automatic data ingestion and model retraining...")
                # Debounce stabilization: wait until file writes settle
                logger.info(f"Waiting {debounce}s for file writes to stabilize...")
                time.sleep(debounce)
                current_fingerprint = get_files_fingerprint(MONITOR_DIRS)

                if _IS_TRAINING_ACTIVE:
                    logger.warning("Training already in progress. Skipping duplicate trigger.")
                    continue

                _IS_TRAINING_ACTIVE = True
                try:
                    # Retrain candidate model
                    logger.info("Triggering data ingestion and candidate model retraining...")
                    metadata = train_classifier()
                    print(f"Retraining successful! New Macro F1: {metadata['macro_f1']:.4f}")

                    if metadata.get("acceptance_passed"):
                        logger.info(f"Candidate passed quality gates! Production updated. Test F1: {metadata['macro_f1']:.4f}")
                        eval_results = evaluate_models()
                        logger.info(f"Evaluation recommendation: {eval_results['decision_criteria']['recommendation']}")
                    else:
                        logger.warning("Candidate model failed quality acceptance criteria. Production model was NOT replaced.")
                except Exception as e:
                    print(f"Error during automated retraining: {e}")
                    logger.error(f"Automated retraining failed: {e}", exc_info=True)
                finally:
                    _IS_TRAINING_ACTIVE = False

                # Update fingerprint
                last_fingerprint = get_files_fingerprint(MONITOR_DIRS)
                print("\nModel updated. Resuming watching for new incoming files...")
                logger.info("Resuming watching for incoming files...")

    except KeyboardInterrupt:
        print("\nWatcher stopped by user.")


if __name__ == "__main__":
    p_interval = None
    d_interval = None
    if len(sys.argv) > 1:
        try:
            p_interval = float(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        try:
            d_interval = float(sys.argv[2])
        except ValueError:
            pass
    watch_and_retrain(poll_interval_seconds=p_interval, debounce_seconds=d_interval)
