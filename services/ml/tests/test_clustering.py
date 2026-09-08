from __future__ import annotations

"""
Spatial-Temporal Clustering Unit Tests (§25.1).
"""

import sys
from pathlib import Path
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from clustering.event_clusterer import assign_cluster, select_cluster_representative


def test_same_location_same_time_cluster_assignment():
    active_clusters = [
        {
            "cluster_id": "cluster_mumbai_001",
            "category": "flood",
            "centroid_lat": 19.076,
            "centroid_lon": 72.878,
            "last_event_at": "2026-09-01T10:00:00Z",
            "member_count": 2
        }
    ]

    event = {
        "category": "flood",
        "latitude": 19.080,
        "longitude": 72.880,
        "timestamp": "2026-09-01T10:10:00Z"
    }

    assigned_id = assign_cluster(event, active_clusters=active_clusters)
    assert assigned_id == "cluster_mumbai_001"


def test_compatible_category_clusters_together():
    active_clusters = [
        {
            "cluster_id": "cluster_heavy_rain_001",
            "category": "heavy_rainfall",
            "centroid_lat": 19.076,
            "centroid_lon": 72.878,
            "last_event_at": "2026-09-01T10:00:00Z",
            "member_count": 1
        }
    ]

    # Flood is compatible with heavy_rainfall (§10.3)
    event = {
        "category": "flood",
        "latitude": 19.078,
        "longitude": 72.879,
        "timestamp": "2026-09-01T10:08:00Z"
    }

    assigned_id = assign_cluster(event, active_clusters=active_clusters)
    assert assigned_id == "cluster_heavy_rain_001"


def test_outside_radius_creates_new_cluster():
    active_clusters = [
        {
            "cluster_id": "cluster_mumbai_001",
            "category": "flood",
            "centroid_lat": 19.076,
            "centroid_lon": 72.878,
            "last_event_at": "2026-09-01T10:00:00Z",
            "member_count": 1
        }
    ]

    # 50 km away (outside 3 km radius)
    event = {
        "category": "flood",
        "latitude": 19.450,
        "longitude": 72.878,
        "timestamp": "2026-09-01T10:05:00Z"
    }

    assigned_id = assign_cluster(event, active_clusters=active_clusters)
    assert assigned_id is None


def test_incompatible_category_not_clustered():
    active_clusters = [
        {
            "cluster_id": "cluster_mumbai_001",
            "category": "flood",
            "centroid_lat": 19.076,
            "centroid_lon": 72.878,
            "last_event_at": "2026-09-01T10:00:00Z",
            "member_count": 1
        }
    ]

    # Heatwave is incompatible with flood
    event = {
        "category": "heatwave",
        "latitude": 19.076,
        "longitude": 72.878,
        "timestamp": "2026-09-01T10:05:00Z"
    }

    assigned_id = assign_cluster(event, active_clusters=active_clusters)
    assert assigned_id is None


def test_representative_selection():
    events = [
        {
            "event_id": "e_low",
            "credibility_score": 0.50,
            "source_trust_score": 0.60,
            "timestamp": "2026-09-01T10:00:00Z"
        },
        {
            "event_id": "e_high",
            "credibility_score": 0.92,
            "source_trust_score": 0.95,
            "timestamp": "2026-09-01T10:05:00Z"
        },
    ]
    rep = select_cluster_representative(events)
    assert rep["event_id"] == "e_high"