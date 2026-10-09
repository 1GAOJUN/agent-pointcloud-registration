"""Phase C minimal readiness checks; no formal run and no GT evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import agent_runner
from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY
from agnnes_agent import build_decision_prompt, parse_agnnes_decision


def test_l3_diagnosis_exposes_robust_gt_free_observations() -> None:
    case = ROOT / "data" / "L3" / "seed_707"
    result = diagnose(str(case / "source.ply"), str(case / "target.ply"))

    assert result["source_point_count"] == 30_000
    assert result["target_point_count"] == 32_400
    assert result["point_count_ratio"] == 1.08
    stats = result["nearest_neighbor_distance_stats"]
    for cloud in ("source", "target"):
        assert set(stats[cloud]) == {
            "sample_size", "median", "p90", "p95", "mad",
            "high_distance_threshold", "high_distance_ratio_proxy",
        }
        assert 0.0 <= stats[cloud]["high_distance_ratio_proxy"] <= 1.0
        assert stats[cloud]["median"] <= stats[cloud]["p90"] <= stats[cloud]["p95"]

    serialized = json.dumps(result).lower()
    for banned in ("gt_transform", "rotation_error", "translation_error"):
        assert banned not in serialized


def test_real_agnes_prompt_stays_anonymous_and_nonheuristic() -> None:
    diagnosis = {
        "source_point_count": 30_000,
        "target_point_count": 32_400,
        "nearest_neighbor_distance_stats": {"source": {}, "target": {}},
    }
    prompt = build_decision_prompt(diagnosis, TOOL_REGISTRY, [])
    lowered = prompt.lower()
    for banned in ("gt_transform", "rotation_error", "translation_error", "seed_707", "data/l3"):
        assert banned not in lowered

    raw = json.dumps({
        "observation_summary": "anonymous geometry observations reviewed",
        "information_sufficient": True,
        "requested_probe": "NONE",
        "probe_reason": "",
        "candidate_methods": [{"method": "LOCAL_ICP", "pros": "low cost", "risks": "local basin"}],
        "selected_method": "LOCAL_ICP",
        "parameter_policy": {"icp_max_corr_scale": 2.0},
        "reasoning_summary": "model-selected test response",
        "confidence": 0.6,
    })
    parsed = parse_agnnes_decision(raw)
    assert parsed["_implementation"] == "agnnes_real"
    assert "heuristic_baseline" not in json.dumps(parsed)

    task = (ROOT / "tasks" / "C_BLIND_RUN_case_unknown_C.md").read_text(encoding="utf-8").lower()
    for banned in ("l3", "noise", "outlier", "gt_transform", "rotation_error", "translation_error"):
        assert banned not in task


def test_retry_returns_observation_to_real_agnes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(agent_runner, "diagnose", lambda *_: {
        "source_point_count": 10,
        "target_point_count": 11,
        "initial_transform_available": True,
        "base_scale": 0.1,
    })
    monkeypatch.setattr(agent_runner, "heuristic_decide", lambda *_: (_ for _ in ()).throw(
        AssertionError("formal path must not call heuristic_decide")))
    monkeypatch.setattr(agent_runner, "heuristic_assess", lambda *_: (_ for _ in ()).throw(
        AssertionError("formal path must not call heuristic_assess")))

    tool_calls = []

    def fake_tool(*_args, **_kwargs):
        tool_calls.append(True)
        fitness = 0.2 if len(tool_calls) == 1 else 0.9
        return {"transform": np.eye(4), "fitness": fitness, "rmse": 0.05, "elapsed_s": 0.01}

    monkeypatch.setattr(agent_runner, "run_local_icp", fake_tool)
    monkeypatch.setattr(agent_runner, "run_global_fpfh_ransac_icp", fake_tool)
    monkeypatch.setattr(agent_runner, "evaluate_agent_result", lambda *_: {
        "success": True, "rot_err_deg": 0.0, "trans_err": 0.0,
    })
    monkeypatch.setattr(agent_runner, "save_evaluator_result", lambda *_: None)
    monkeypatch.setattr(agent_runner, "_write_run_summary", lambda *_: None)

    seen_prior = []

    def decide(_diagnosis, _tools, prior):
        seen_prior.append(json.loads(json.dumps(prior)))
        if prior:
            assert prior[-1]["observation"]["fitness"] == 0.2
            assert prior[-1]["assessment"]["decision"] == "RETRY"
            return {"selected_method": "GLOBAL_FPFH_RANSAC_ICP", "parameter_policy": {
                "global_corr_scale": 4.0, "icp_max_corr_scale": 1.5,
            }}
        return {"selected_method": "LOCAL_ICP", "parameter_policy": {"icp_max_corr_scale": 2.0}}

    def assess(observation, _prior):
        if observation["fitness"] < 0.5:
            return {
                "decision": "RETRY", "reason": "quality insufficient",
                "next_method": "GLOBAL_FPFH_RANSAC_ICP",
                "next_parameter_policy": {"global_corr_scale": 4.0, "icp_max_corr_scale": 1.5},
            }
        return {"decision": "ACCEPT", "reason": "quality sufficient", "next_method": None}

    result = agent_runner.run_agent_case(
        "anonymous_source", "anonymous_target", str(tmp_path / "run"), "evaluator_only_gt",
        max_retry=2, agnes_decide_fn=decide, agnes_assess_fn=assess,
    )
    assert len(tool_calls) == 2
    assert len(seen_prior) == 2 and seen_prior[0] == []
    assert result["final_decision"] == "ACCEPT"
    run_log = json.loads((tmp_path / "run" / "agh_run_log.json").read_text(encoding="utf-8"))
    assert run_log["decision_implementation"] == "agnnes_real"
    assert "evaluator_only_gt" not in json.dumps(seen_prior)
