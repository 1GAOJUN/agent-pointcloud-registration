"""The current formal Run owns its C.1 prompt snapshots."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_current_run_receives_current_decision_and_assessment_prompts(tmp_path: Path) -> None:
    run = tmp_path / "new_anonymous_run"
    agent = run / "02_AGENT"
    _write(agent / "diagnosis.json", {"fixture_marker": "CURRENT_RUN_ONLY", "base_scale": 0.1})
    _write(agent / "probe_observation_01.json", {
        "probe_name": "PCA_ORIENTATION",
        "orientation_confidence": "LOW",
        "ambiguity_detected": True,
        "ambiguity_reason": "near_line_degeneracy",
    })
    _write(agent / "probe_observation_02.json", {
        "probe_name": "CHEAP_LOCAL_ICP", "fitness_improvement": 0.01,
    })
    _write(agent / "observation_01.json", {
        "tool_name": "LOCAL_ICP", "parameter_policy_used": {"icp_max_corr_scale": 1.5},
        "fitness": 0.99, "rmse": 0.01,
    })

    subprocess.run([
        sys.executable, str(ROOT / "tests/_c_decision_prompt.py"),
        "--run-dir", str(run), "--round", "3",
    ], cwd=ROOT, check=True, capture_output=True, text=True)
    subprocess.run([
        sys.executable, str(ROOT / "tests/_c_assessment_prompt.py"),
        "--run-dir", str(run), "--attempt", "1",
    ], cwd=ROOT, check=True, capture_output=True, text=True)

    decision_path = run / "01_AGH/agnnes_decision_prompt_03.json"
    assessment_path = run / "01_AGH/agnnes_assessment_prompt_attempt_01.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assessment = json.loads(assessment_path.read_text(encoding="utf-8"))

    assert decision["meta"]["run_id"] == run.name
    assert assessment["meta"]["run_id"] == run.name
    assert decision["prompt"]["diagnosis"]["fixture_marker"] == "CURRENT_RUN_ONLY"
    decision_notes = " ".join(decision["prompt"]["notes"]).lower()
    assert "local-optimum risk" in decision_notes
    assert "globally correct pose" in decision_notes
    assessment_notes = " ".join(assessment["prompt"]["notes"]).lower()
    assert "not, by themselves, proof" in assessment_notes
    assert "local-optimum risk" in assessment_notes
    assert assessment["prompt"]["probe_observations"][0]["ambiguity_detected"] is True
    schema = assessment["prompt"]["output_schema"]
    assert {"global_consistency_assessment", "local_optimum_risk", "evidence_conflicts"} <= set(schema)

    serialized = json.dumps({"decision": decision, "assessment": assessment}).lower()
    for forbidden in ("gt_transform", "rotation_error", "translation_error"):
        assert forbidden not in serialized
