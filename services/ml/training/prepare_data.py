from __future__ import annotations

"""
Universal Data Ingestion & Preparation Script (§4.10, §19.2).
Automatically discovers, parses, cleans, and converts ANY CSV or JSON dataset
in the data/ directory into production-ready training data.
Universal Data Ingestion, Validation & Preparation Pipeline (§4.10, §19.2).
Strictly validates training data before preparation:
1. Rejects unknown categories by default (never silently sinking into 'other')
2. Enforces minimum text length and non-empty content
3. Deduplicates identical records
4. Configurable validation policy ('reject' | 'skip' | 'warn')
"""

import sys
from pathlib import Path
import json
import logging
from typing import Any
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ..classifier.rules import (
        VALID_CATEGORIES,
        canonicalize_category,
        validate_category,
        InvalidCategoryError,
    )
    from ..config.config_loader import load_ml_config
    from ..utils.text import normalize_text
except (ImportError, ValueError):
    from classifier.rules import (
        VALID_CATEGORIES,
        canonicalize_category,
        validate_category,
        InvalidCategoryError,
    )
    from config.config_loader import load_ml_config
    from utils.text import normalize_text

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"
OUTPUT_FILE = OUTPUT_DIR / "cleaned_training_data.csv"

class DatasetValidationError(ValueError):
    """Raised when training data fails quality validation."""
    def __init__(self, message: str, report: dict | None = None):
        super().__init__(message)
        self.report = report or {}


def load_from_json(json_path: Path) -> list[dict]:
    """Parse JSON files (list of dicts or {"events": [...]})."""
    records = []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            raw_list = data.get("events") or data.get("data") or data.get("records") or [data]
        elif isinstance(data, list):
            raw_list = data
        else:
            raw_list = []

        for idx, item in enumerate(raw_list):
            if not isinstance(item, dict):
                continue

            desc = (
                item.get("description") or
                item.get("text") or
                item.get("event", {}).get("description") or
                item.get("event_description") or
                ""
            )
            cat = (
                item.get("category") or
                item.get("event_type") or
                item.get("label") or
                item.get("category_label") or
                item.get("event", {}).get("category") or
                item.get("type") or
                ""
            )

            # Skip telemetry items that are not event reports (having neither text nor category)
            if not desc and not cat:
                continue

            event_id = item.get("event_id") or item.get("id")
            source = item.get("source")
            source_id = (
                item.get("source_id") or
                (source.get("name") if isinstance(source, dict) else None) or
                item.get("source_name")
            )

            records.append({
                "text": str(desc),
                "category": str(cat) if cat is not None else "",
                "event_id": str(event_id) if event_id is not None else None,
                "source_id": str(source_id) if source_id is not None else None,
                "_file": str(json_path.name),
                "_row": idx + 1,
            })
    except Exception as e:
        raise DatasetValidationError(f"Could not parse JSON {json_path}: {e}") from e

    return records


def load_from_csv(csv_path: Path) -> list[dict]:
    """Parse CSV files with flexible column headers."""
    records = []
    try:
        df = pd.read_csv(csv_path)
        col_map = {}
        for col in df.columns:
            c_clean = col.strip().lower()
            if c_clean in ("text", "description", "event_description", "report", "content"):
                col_map[col] = "text"
            elif c_clean in ("category", "event_type", "label", "category_label", "type"):
                col_map[col] = "category"
            elif c_clean in ("event_id", "id"):
                col_map[col] = "event_id"
            elif c_clean in ("source_id", "source", "source_name"):
                col_map[col] = "source_id"

        df = df.rename(columns=col_map)
        has_text = "text" in df.columns
        has_cat = "category" in df.columns

        if not has_text or not has_cat:
            missing = []
            if not has_text:
                missing.append("text")
            if not has_cat:
                missing.append("category")
            raise DatasetValidationError(
                f"CSV file {csv_path.name} missing required columns: {missing}. Columns present: {list(df.columns)}"
            )

        has_event_id = "event_id" in df.columns
        has_source_id = "source_id" in df.columns

        for idx, row in df.iterrows():
            records.append({
                "text": str(row["text"]) if pd.notna(row["text"]) else "",
                "category": str(row["category"]) if pd.notna(row["category"]) else "",
                "event_id": str(row["event_id"]) if has_event_id and pd.notna(row["event_id"]) else None,
                "source_id": str(row["source_id"]) if has_source_id and pd.notna(row["source_id"]) else None,
                "_file": str(csv_path.name),
                "_row": idx + 2,  # 1-based index including header
            })
    except Exception as e:
        if isinstance(e, DatasetValidationError):
            raise
        raise DatasetValidationError(f"Could not parse CSV {csv_path}: {e}") from e

    return records


def discover_data_files(custom_path: Path | str | None = None) -> list[Path]:
    """Discover all CSV and JSON data files in data/ directory.

    Files are deduplicated by their **resolved absolute path** so that the
    same physical file placed in multiple scan directories (e.g., a JSON file
    that was copied from data/incoming/ to data/raw/ for archival purposes) is
    ingested exactly once.  The first occurrence in discovery-priority order
    wins:  data/training > data/incoming > data/raw.

    A WARNING is logged for every suppressed duplicate so the operator is
    aware that a physical copy exists on disk and can remove it.  This avoids
    silent data duplication that deduplication-on-text would otherwise mask.

    This design is intentionally dataset-size agnostic: it uses resolved path
    identity (O(n) in the number of files, not records) and is correct whether
    the data directory contains one file or hundreds of event-category files.
    """
    if custom_path:
        p = Path(custom_path)
        if p.is_file():
            return [p]
        elif p.is_dir():
            raw = list(p.glob("**/*.csv")) + list(p.glob("**/*.json"))
        else:
            raw = []
    else:
        # Discovery order: data/training > data/incoming > data/raw.
        raw = []
        for sub in ["training", "incoming", "raw"]:
            sub_dir = DATA_DIR / sub
            if sub_dir.exists():
                raw.extend(list(sub_dir.glob("*.csv")))
                raw.extend(list(sub_dir.glob("*.json")))

        if not raw:
            raw = list(DATA_DIR.glob("*.csv")) + list(DATA_DIR.glob("*.json"))

    # Exclude already-processed output file.
    output_resolved = OUTPUT_FILE.resolve()
    raw = [f for f in raw if f.resolve() != output_resolved]

    # Deduplicate by resolved absolute path (preserves discovery-order priority).
    seen_resolved: dict[Path, Path] = {}   # resolved_path -> first canonical Path
    for f in raw:
        resolved = f.resolve()
        if resolved in seen_resolved:
            first = seen_resolved[resolved]
            logger.warning(
                "Duplicate data file suppressed: '%s' resolves to the same physical "
                "file as '%s' (already scheduled for ingestion). "
                "Remove the duplicate copy to avoid confusion.",
                f,
                first,
            )
        else:
            seen_resolved[resolved] = f

    return list(seen_resolved.values())


def prepare_training_data(
    input_path: Path | str | None = None,
    output_path: Path | str | None = None,
    validation_policy: str | None = None
) -> tuple[pd.DataFrame, dict]:
    """
    Ingest, clean, normalize, and prepare labelled data from any file or data/ folder.
    
    validation_policy:
      - 'reject' (default): Fails immediately if any invalid category or malformed record is found.
      - 'skip': Silently drops bad records and continues.
      - 'warn': Logs warnings for bad records and skips them.
    """
    cfg = load_ml_config()
    policy = (
        validation_policy or
        cfg.get("training", {}).get("validation_policy", "reject")
    ).lower()

    discovered_files = discover_data_files(input_path)
    if not discovered_files:
        raise FileNotFoundError(
            f"No data files (.csv or .json) found in {input_path or DATA_DIR}."
        )

    print(f"Discovered {len(discovered_files)} dataset file(s): {[f.name for f in discovered_files]}")

    per_file_counts = {}
    all_raw_records = []

    for file_path in discovered_files:
        try:
            if file_path.suffix.lower() == ".csv":
                recs = load_from_csv(file_path)
            elif file_path.suffix.lower() == ".json":
                recs = load_from_json(file_path)
            else:
                continue
        except DatasetValidationError as e:
            if policy == "reject":
                raise
            logger.warning("Skipping malformed dataset file %s: %s", file_path, e)
            per_file_counts[file_path.name] = 0
            continue

        per_file_counts[file_path.name] = len(recs)
        all_raw_records.extend(recs)

    if not all_raw_records:
        raise DatasetValidationError("No data records could be extracted from input files.")

    # Validation Phase
    valid_records = []
    empty_text_dropped = 0
    short_text_dropped = 0
    invalid_categories = []

    for rec in all_raw_records:
        raw_text = rec["text"]
        raw_cat = rec["category"]
        fname = rec["_file"]
        row_num = rec["_row"]

        # Text check
        norm_text = normalize_text(raw_text)
        if len(norm_text) == 0:
            empty_text_dropped += 1
            if policy == "reject":
                raise DatasetValidationError(
                    f"Empty text in file '{fname}', row {row_num}."
                )
            continue

        if len(norm_text) < 3:
            short_text_dropped += 1
            if policy == "reject":
                raise DatasetValidationError(
                    f"Text too short ('{norm_text}') in file '{fname}', row {row_num}."
                )
            continue

        # Category check
        try:
            canonical_cat = validate_category(raw_cat, file_path=fname, row_index=row_num)
        except InvalidCategoryError as e:
            invalid_categories.append({
                "file": fname,
                "row": row_num,
                "value": raw_cat,
                "error": str(e)
            })
            if policy == "reject":
                raise DatasetValidationError(
                    f"Dataset validation failed: {str(e)}",
                    report={"invalid_categories": invalid_categories}
                ) from e
            continue

        valid_records.append({
            "text": norm_text,
            "category": canonical_cat,
            "event_id": rec.get("event_id"),
            "source_id": rec.get("source_id"),
        })

    if not valid_records:
        raise DatasetValidationError(
            f"No valid records remained after validation! Dropped: empty={empty_text_dropped}, "
            f"short={short_text_dropped}, invalid_categories={len(invalid_categories)}"
        )

    df = pd.DataFrame(valid_records)

    # Deduplication
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["text", "category"])
    duplicates_removed = before_dedup - len(df)

    class_distribution = df["category"].value_counts().to_dict()

    summary = {
        "files_ingested": [f.name for f in discovered_files],
        "per_file_extracted_events": per_file_counts,
        "total_extracted_records": len(all_raw_records),
        "empty_text_dropped": empty_text_dropped,
        "short_text_dropped": short_text_dropped,
        "invalid_categories_dropped": len(invalid_categories),
        "duplicates_removed": duplicates_removed,
        "final_unique_training_records": len(df),
        "categories_present": len(class_distribution),
        "class_distribution": class_distribution,
    }

    # Save cleaned training data
    out_target = Path(output_path) if output_path else OUTPUT_FILE
    out_target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_target, index=False)

    print(f"Extracted events breakdown: {per_file_counts}")
    print(f"Total extracted: {len(all_raw_records)} events | Duplicates filtered: {duplicates_removed}")
    print(f"Final unique clean dataset saved to {out_target} ({len(df)} records across {len(class_distribution)} categories).")

    return df, summary


if __name__ == "__main__":
    _, report = prepare_training_data()
    print("\nData Preparation Report:")
    print(json.dumps(report, indent=2))
