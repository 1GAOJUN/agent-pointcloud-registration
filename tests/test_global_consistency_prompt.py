"""Targeted checks for evidence-aware Real Agnes assessment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agnnes_agent import AgnesDecisionAdapter, build_assessment_prompt, validate_assessment


AMBIGUOUS_PROBES = [
    {
        "probe_name": "PCA_ORIENTATION",
        "orientation_confidence": "LOW",
        "rotation_estimate_deg": None,
        "ambiguity_detected": True,
        "ambiguity_reason": "near_line_degeneracy; transverse axes undetermined",
    },
    {
        "probe_name": "CHEAP_LOCAL_ICP",
        "initial_fitness": 0.51,
        "probe_fitness": 0.52,
        "fitness_improvement": 0.01,
    },
]


def _valid_response(decision: str = "ACCEPT") -> str:
    return json.dumps({
        "assessment": "Observable evidence reviewed.",
        "global_consistency_assessment": "Ambiguity remains; acceptance would require an explicit justification.",
        "local_optimum_risk": "HIGH",
        "evidence_conflicts": ["orientation ambiguity conflicts with a purely local quality claim"],
        "decision": decision,
        "reason": "Professional model judgment based on the complete observable record.",
        "next_method": None,
        "next_parameter_policy": None,
        "confidence": 0.5,
    })


def test_high_fitness_is_not_absolute_and_probe_ambiguity_reaches_assessment() -> None:
    prompt = json.loads(build_assessment_prompt(
        observation={"fitness": 0.99, "rmse": 0.01, "tool_name": "LOCAL_ICP"},
        prior_attempts=[],
        current_method="LOCAL_ICP",
        current_policy={"icp_max_corr_scale": 1.5},
        probe_observations=AMBIGUOUS_PROBES,
    ))
    assert prompt["probe_observations"] == AMBIGUOUS_PROBES
    notes = " ".join(prompt["notes"]).lower()
    assert "not, by themselves, proof" in notes
    assert "local-optimum risk" in notes
    assert prompt["output_schema"]["local_optimum_risk"] == "LOW | MEDIUM | HIGH | UNKNOWN"
    serialized = json.dumps(prompt).lower()
    for forbidden in ("gt_transform", "rotation_error", "translation_error"):
        assert forbidden not in serialized


def test_adapter_forwards_probe_context_without_python_verdict_override() -> None:
    captured: dict[str, object] = {}

    def raw_assessment(prompt: str) -> str:
        captured.update(json.loads(prompt))
        return _valid_response("ACCEPT")

    adapter = AgnesDecisionAdapter(
        get_raw_decision=lambda _prompt: "{}",
        get_raw_assessment=raw_assessment,
        probe_observations_fn=lambda: AMBIGUOUS_PROBES,
    )
    result = adapter.assess({
        "fitness": 0.99,
        "rmse": 0.01,
        "tool_name": "LOCAL_ICP",
        "parameter_policy_used": {"icp_max_corr_scale": 1.5},
    })
    assert captured["probe_observations"] == AMBIGUOUS_PROBES
    assert result["decision"] == "ACCEPT"
    assert result["_implementation"] == "agnnes_real"
    assert validate_assessment(json.loads(_valid_response("RETRY"))) is None
