from pathlib import Path
import sys

import numpy as np
import open3d as o3d

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_probes import _bidirectional_correspondence_support


def _cloud(points):
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(
        np.asarray(points, dtype=np.float64).reshape((-1, 3)))
    return cloud


def test_bidirectional_support_schema_and_asymmetry():
    source = _cloud([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]])
    target = _cloud([[0, 0, 0], [1, 0, 0]])
    result = _bidirectional_correspondence_support(source, target, np.eye(4), 0.01)

    assert result == {
        "source_to_target_support": 0.5,
        "target_to_source_support": 1.0,
        "bidirectional_support": 2.0 / 3.0,
        "support_confidence": "HIGH",
        "support_distance_threshold": 0.01,
    }


def test_support_is_gt_free_and_contains_no_method_policy():
    result = _bidirectional_correspondence_support(
        _cloud([[0, 0, 0]]), _cloud([[0, 0, 0]]), np.eye(4), 0.1)
    forbidden = {
        "gt_transform", "rotation_error", "translation_error", "overlap_ratio",
        "selected_method", "parameter_policy", "verdict",
    }
    assert forbidden.isdisjoint(result)


def test_empty_input_fails_observation_confidence_closed():
    result = _bidirectional_correspondence_support(
        _cloud([]), _cloud([[0, 0, 0]]), np.eye(4), 0.1)
    assert result["bidirectional_support"] is None
    assert result["support_confidence"] == "LOW"
