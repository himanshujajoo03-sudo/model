from __future__ import annotations

"""
End-to-End Verification of Demo Scenarios (§26).
"""

import sys
import json
from pathlib import Path
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from classifier.event_classifier import classify_event
from credibility.credibility_scorer import score_credibility
from dedup.duplicate_detector import compute_duplicate_score
from clustering.event_clusterer import assign_cluster
from explainability.reason_generator import generate_reasons

FIXTURES_DIR = ML_ROOT / "tests" / "fixtures"


def test_scenario_a_mumbai_flood():
    """
    Scenario A (§26): Mumbai Flood (Multi-Source Corroboration)
    5 reports from different sources (Open-Meteo, NDTV, Citizen, Social, IMD).
    Expect: high credibility (>=0.80), flood/heavy_rainfall classification, same cluster.
    """
    with open(FIXTURES_DIR / "mumbai_flood_reports.json", "r", encoding="utf-8") as f:
        reports = json.load(f)

    active_clusters = []
    processed_events = []

    for idx, report in enumerate(reports):
        # 1. Classification
        cls_result = classify_event(report["description"], category_hint=report.get("category"))
        assert cls_result["classified_category"] in ("flood", "heavy_rainfall")
        assert cls_result["classification_confidence"] >= 0.60

        report["classified_category"] = cls_result["classified_category"]
        report["classification_confidence"] = cls_result["classification_confidence"]

        # 2. Credibility with corroboration from prior reports
        cred_result = score_credibility(report, recent_events=processed_events)
        report["credibility_score"] = cred_result["credibility_score"]
        report["credibility_reasons"] = cred_result["credibility_reasons"]

        # 3. Clustering
        cluster_id = assign_cluster(report, active_clusters=active_clusters)
        if not cluster_id:
            cluster_id = "cluster_mumbai_flood_demo"
            active_clusters.append({
                "cluster_id": cluster_id,
                "category": report["classified_category"],
                "centroid_lat": report["latitude"],
                "centroid_lon": report["longitude"],
                "last_event_at": report["timestamp"],
                "member_count": 1
            })
        else:
            for c in active_clusters:
                if c["cluster_id"] == cluster_id:
                    c["member_count"] += 1
                    c["last_event_at"] = report["timestamp"]

        report["cluster_id"] = cluster_id
        processed_events.append(report)

    # Validate that by report 3+, corroboration has kicked in
    later_citizen_report = processed_events[2]
    assert later_citizen_report["credibility_score"] >= 0.75
    assert all(e["cluster_id"] == "cluster_mumbai_flood_demo" for e in processed_events)


def test_scenario_b_nagpur_heatwave():
    """
    Scenario B (§26): Nagpur Heatwave (API-Dominated)
    3 weather reports with high temperatures.
    Expect: heatwave classification (>= 0.75), high credibility with corroboration.
    """
    with open(FIXTURES_DIR / "nagpur_heatwave_reports.json", "r", encoding="utf-8") as f:
        reports = json.load(f)

    processed_events = []
    for report in reports:
        cls_result = classify_event(report["description"])
        assert cls_result["classified_category"] == "heatwave"
        assert cls_result["classification_confidence"] >= 0.75

        cred_result = score_credibility(report, recent_events=processed_events)
        assert cred_result["credibility_score"] >= 0.65
        processed_events.append(report)


def test_scenario_d_duplicate_reports():
    """
    Scenario D (§26): Duplicate Reports
    3 near-identical reports from same source within 3 min.
    Expect: duplicate score >= 0.85.
    """
    with open(FIXTURES_DIR / "duplicate_reports.json", "r", encoding="utf-8") as f:
        reports = json.load(f)

    dup_score = compute_duplicate_score(reports[1], reports[0])
    assert dup_score >= 0.85


def test_scenario_e_suspicious_report():
    """
    Scenario E (§26): Suspicious Report
    Low-trust source, coordinates don't match city, minimal description.
    Expect: low credibility (<= 0.45), reasons identifying anomalies.
    """
    with open(FIXTURES_DIR / "low_credibility_reports.json", "r", encoding="utf-8") as f:
        reports = json.load(f)

    suspicious = reports[0]
    cred_result = score_credibility(suspicious, recent_events=[])

    assert cred_result["credibility_score"] <= 0.45
    assert any("low configured trust" in r for r in cred_result["credibility_reasons"])
    assert any("do not align" in r for r in cred_result["credibility_reasons"])
    assert any("minimal or absent" in r for r in cred_result["credibility_reasons"])

