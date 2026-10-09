"""Minimal evidence-only post-processing tests."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import open3d as o3d

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from postprocess_run import DERIVED_RELATIVE_PATHS, postprocess_run


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _ply(path: Path, points: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    assert o3d.io.write_point_cloud(str(path), cloud, write_ascii=True)


def _hashes(root: Path, excluded: set[Path] | None = None) -> dict[str, str]:
    excluded = excluded or set()
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root) not in excluded
    }


def test_complete_multi_attempt_run_is_idempotent_and_preserves_core(tmp_path: Path) -> None:
    run = tmp_path / "formal_run"
    rng = np.random.RandomState(7)
    source = rng.normal(size=(120, 3))
    transform = np.eye(4)
    transform[:3, 3] = [0.4, -0.2, 0.1]
    target = source + transform[:3, 3]
    _ply(run / "inputs/source.ply", source)
    _ply(run / "inputs/target.ply", target)
    _json(run / "00_INDEX/run_manifest.json", {"run_id": "fixture_multi_attempt"})
    _json(run / "02_AGENT/diagnosis.json", {"source_point_count": 120, "target_point_count": 120})
    _json(run / "02_AGENT/agnnes_decision_01_parsed.json", {"selected_method": "LOCAL_ICP", "parameter_policy": {"icp_max_corr_scale": 1.0}})
    _json(run / "02_AGENT/decision_final.json", {"selected_method": "GLOBAL_FPFH_RANSAC_ICP", "parameter_policy": {"global_corr_scale": 4.0, "icp_max_corr_scale": 1.0}})
    _json(run / "02_AGENT/observation_01.json", {"transform": transform.tolist(), "fitness": 1.0, "rmse": 0.0, "elapsed_s": 0.2, "tool_name": "GLOBAL_FPFH_RANSAC_ICP"})
    _json(run / "02_AGENT/metrics.json", {"fitness": 1.0, "rmse": 0.0, "elapsed_s": 0.2, "tool_name": "GLOBAL_FPFH_RANSAC_ICP"})
    _json(run / "02_AGENT/agent_final_assessment.json", {"decision": "ACCEPT"})
    _json(run / "04_CONFIG/parameters.json", {"agnnes_multiplier": {"global_corr_scale": 4.0}, "derived_actual_parameters": {"ransac_max_correspondence_distance": 0.12}})
    _json(run / "05_VALIDATION/evaluator_result.json", {"estimated_transform": transform.tolist(), "rot_err_deg": 0.0, "trans_err": 0.0, "success": True})
    for number, verdict, fitness in ((1, "RETRY", 0.2), (2, "ACCEPT", 1.0)):
        attempt = run / f"attempts/attempt_{number:02d}"
        _json(attempt / "attempt_summary.json", {"attempt_no": number, "method": "LOCAL_ICP" if number == 1 else "GLOBAL_FPFH_RANSAC_ICP", "parameter_policy": {"scale": number}, "fitness": fitness, "rmse": 0.1 / number, "final_agent_decision": verdict, "retried": number == 1})
        _json(attempt / "metrics.json", {"fitness": fitness, "rmse": 0.1 / number, "elapsed_s": 0.1 * number})
        _json(attempt / "parameters.json", {"derived_actual_parameters": {"distance": 0.01 * number}})

    core_before = _hashes(run, DERIVED_RELATIVE_PATHS)
    first = postprocess_run(run)
    generated_first = _hashes(run)
    second = postprocess_run(run)
    generated_second = _hashes(run)

    assert first == second
    assert first["status"] == "COMPLETE"
    assert first["attempt_count"] == 2 and first["retry_occurred"] is True
    assert core_before == _hashes(run, DERIVED_RELATIVE_PATHS)
    assert generated_first == generated_second
    for relative in DERIVED_RELATIVE_PATHS:
        assert (run / relative).is_file()
    report = (run / "00_INDEX/run_summary.md").read_text(encoding="utf-8")
    assert "| 1 |" in report and "| 2 |" in report and "RETRY" in report


def test_incomplete_run_reports_missing_without_visuals(tmp_path: Path) -> None:
    run = tmp_path / "partial_run"
    _json(run / "02_AGENT/diagnosis.json", {"source_point_count": 10})
    summary = postprocess_run(run)
    assert summary["status"] == "INTERRUPTED"
    assert "estimated_transform" in summary["missing_items"]
    assert not (run / "06_VISUALS").exists()
    assert "No success result" in (run / "00_INDEX/run_summary.md").read_text(encoding="utf-8")


def test_flat_formal_run_uses_root_evidence_and_anonymous_case_reference(tmp_path: Path) -> None:
    run = tmp_path / "flat_run"
    case = tmp_path / "anonymous_case"
    agent_input = case / "agent_input"
    evaluator_only = case / "evaluator_only"
    rng = np.random.RandomState(11)
    source = rng.normal(size=(100, 3))
    transform = np.eye(4)
    transform[:3, 3] = [0.2, 0.1, -0.1]
    _ply(agent_input / "source_cloud.ply", source)
    _ply(agent_input / "target_cloud.ply", source + transform[:3, 3])
    evaluator_only.mkdir(parents=True)

    _json(run / "diagnosis.json", {"source_point_count": 100, "target_point_count": 100})
    _json(run / "decision_01.json", {"selected_method": "LOCAL_ICP", "parameter_policy": {"icp_max_corr_scale": 2.0}})
    _json(run / "decision_final.json", {"selected_method": "LOCAL_ICP", "parameter_policy": {"icp_max_corr_scale": 2.0}})
    _json(run / "observation_01.json", {"transform": transform.tolist(), "fitness": 0.983, "rmse": 0.01616, "elapsed_s": 0.9, "tool_name": "LOCAL_ICP", "parameter_policy_used": {"icp_max_corr_scale": 2.0}})
    _json(run / "agent_final_assessment.json", {"decision": "ACCEPT"})
    _json(run / "parameters.json", {"final_selected_method": "LOCAL_ICP", "final_parameter_policy": {"icp_max_corr_scale": 2.0}})
    _json(run / "evaluator_result.json", {"gt_path": str(evaluator_only / "gt_transform.npy"), "rot_err_deg": 50.77, "trans_err": 0.0043, "success": False})
    (run / "attempts/attempt_01").mkdir(parents=True)

    summary = postprocess_run(run)
    assert summary["status"] == "COMPLETE"
    assert summary["selected_method"] == "LOCAL_ICP"
    assert summary["fitness"] == 0.983
    assert summary["gt_rotation_error_deg"] == 50.77
    assert summary["final_result"] is False
    assert summary["attempt_count"] == 1
    assert summary["attempts"][0]["method"] == "LOCAL_ICP"
    assert summary["attempts"][0]["fitness"] == 0.983
    for relative in DERIVED_RELATIVE_PATHS:
        assert (run / relative).is_file()


def test_flat_multi_attempt_partial_overlap_run(tmp_path: Path) -> None:
    run = tmp_path / "flat_multi"
    case = tmp_path / "case" / "agent_input"
    rng = np.random.RandomState(17)
    source = rng.normal(size=(120, 3))
    target = source[:70] + np.array([0.2, 0.0, 0.0])
    transform = np.eye(4); transform[0, 3] = 0.2
    _ply(case / "source_cloud.ply", source); _ply(case / "target_cloud.ply", target)
    _json(run / "diagnosis.json", {"point_count_ratio": 70 / 120})
    for number, method, verdict, fitness in (
        (1, "GLOBAL_FPFH_RANSAC_ICP", "RETRY", 0.5),
        (2, "LOCAL_ICP", "ABORT", 0.6),
    ):
        suffix = f"{number:02d}"
        _json(run / f"decision_{suffix}.json", {"selected_method": method, "parameter_policy": {"scale": number}})
        _json(run / f"observation_{suffix}.json", {"transform": transform.tolist(), "fitness": fitness, "rmse": 0.01, "wall_clock_s": number, "tool_name": method, "max_correspondence_distance": 0.1})
        _json(run / f"agent_assessment_{suffix}.json", {"decision": verdict})
    _json(run / "decision_final.json", {"selected_method": "LOCAL_ICP", "parameter_policy": {"scale": 2}})
    _json(run / "final_transform.json", {"transform": transform.tolist()})
    _json(run / "agent_final_assessment.json", {"decision": "ABORT"})
    _json(run / "parameters.json", {"final_selected_method": "LOCAL_ICP"})
    _json(run / "probe_02.json", {"support_distance_threshold": 0.1})
    evaluator_only = case.parent / "evaluator_only"; evaluator_only.mkdir(parents=True)
    _json(run / "evaluator_result.json", {"gt_path": str(evaluator_only / "gt_transform.npy"), "success": True})

    summary = postprocess_run(run)
    assert summary["status"] == "COMPLETE"
    assert summary["attempt_count"] == 2 and summary["retry_occurred"] is True
    assert [item["verdict"] for item in summary["attempts"]] == ["RETRY", "ABORT"]
    assert summary["agent_verdict"] == "ABORT" and summary["final_result"] is True
    assert (run / "06_VISUALS/overlap_detail.png").is_file()
