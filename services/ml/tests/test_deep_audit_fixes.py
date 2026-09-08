from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pytest

from classifier.rule_based_classifier import RuleBasedClassifier
from credibility.credibility_scorer import score_credibility
from training.prepare_data import load_from_json, DatasetValidationError
from training.train import leakage_safe_split


def test_rule_classifier_handles_negation():
    c=RuleBasedClassifier()
    assert c.predict("There is no flood in the city")["classified_category"] != "flood"
    assert c.predict("No rain was reported")["classified_category"] != "rainfall"
    assert c.predict("Flooding did not occur")["classified_category"] != "flood"


def test_rule_classifier_does_not_match_400_as_40():
    c=RuleBasedClassifier()
    result=c.predict("temperature above 400 degrees")
    assert result["classified_category"] != "heatwave"


def test_credibility_accepts_integration_aliases():
    event={"description":"Flood in Mumbai", "category":"flood"}
    result=score_credibility(event, corroboration=0.9, weather_agreement=1.0,
                             temporal_consistency=0.8, spatial_consistency=0.9,
                             content_quality=0.9)
    assert result["factors"]["corroboration"] == 0.9
    assert result["factors"]["weather_agreement"] == 1.0
    assert result["factors"]["temporal_consistency"] == 0.8
    assert result["factors"]["spatial_consistency"] == 0.9
    assert result["factors"]["content_quality"] == 0.9


def test_malformed_json_raises(tmp_path):
    p=tmp_path/"bad.json"; p.write_text('{bad', encoding='utf-8')
    with pytest.raises(DatasetValidationError): load_from_json(p)


def test_grouped_split_prevents_near_duplicate_leakage():
    rows=[]
    for i in range(60):
        cat=["flood","other","strong_wind"][i%3]
        text=f"{cat} report number {i}"
        eid=f"e{i//2}" if i%2==0 else None
        rows.append((text,cat,eid))
    rows[1]=(rows[0][0]+" around pune", rows[0][1], rows[0][2])
    df=pd.DataFrame(rows,columns=["text","category","event_id"])
    tr,va,te,groups=leakage_safe_split(df,{"train":.8,"val":.1,"test":.1},42,.85)
    assert not (set(groups.loc[tr]) & set(groups.loc[va]))
    assert not (set(groups.loc[tr]) & set(groups.loc[te]))
    assert not (set(groups.loc[va]) & set(groups.loc[te]))


def _make_grouped_dataset(groups_per_class=12, records_per_group=2):
    rows = []
    for cat in ("flood", "other", "strong_wind"):
        for g in range(groups_per_class):
            eid = f"{cat}-event-{g}"
            for r in range(records_per_group):
                rows.append({
                    "text": f"{cat} independent event {g} observation {r}",
                    "category": cat,
                    "event_id": eid,
                })
    return pd.DataFrame(rows)


def test_grouped_split_rejects_too_few_distinct_groups():
    """Raw sample counts can be large while group-based 3-way splitting is impossible."""
    rows = []
    for cat in ("flood", "other"):
        for i in range(20):
            rows.append({
                "text": f"{cat} repeated observation {i}",
                "category": cat,
                "event_id": f"{cat}-only-event",
            })
    df = pd.DataFrame(rows)
    with pytest.raises(Exception, match="distinct leakage group"):
        leakage_safe_split(df, {"train": .8, "val": .1, "test": .1}, 42, .85)


def test_grouped_split_rejects_empty_holdout_instead_of_returning_it():
    """Two groups/class must fail clearly rather than selecting an empty SGKF fold."""
    rows = []
    for cat in ("flood", "other"):
        for g in range(2):
            for r in range(20):
                rows.append({
                    "text": f"{cat} event group {g} observation {r}",
                    "category": cat,
                    "event_id": f"{cat}-{g}",
                })
    df = pd.DataFrame(rows)
    with pytest.raises(Exception, match="distinct leakage group"):
        leakage_safe_split(df, {"train": .8, "val": .1, "test": .1}, 42, .85)


def test_grouped_split_honors_non_default_ratios():
    """Configured 70/15/15 must not silently become 80/10/10."""
    df = _make_grouped_dataset(groups_per_class=20, records_per_group=2)
    cfg = {"train": .70, "val": .15, "test": .15}
    tr, va, te, groups = leakage_safe_split(df, cfg, 42, .85)
    ratios = {
        "train": len(tr) / len(df),
        "val": len(va) / len(df),
        "test": len(te) / len(df),
    }
    assert ratios["test"] > 0.11
    assert ratios["val"] > 0.11
    assert abs(ratios["train"] - .70) < .10
    assert abs(ratios["val"] - .15) < .10
    assert abs(ratios["test"] - .15) < .10
    assert abs(sum(ratios.values()) - 1.0) < 1e-9
    assert not (set(groups.loc[tr]) & set(groups.loc[va]))
    assert not (set(groups.loc[tr]) & set(groups.loc[te]))
    assert not (set(groups.loc[va]) & set(groups.loc[te]))
