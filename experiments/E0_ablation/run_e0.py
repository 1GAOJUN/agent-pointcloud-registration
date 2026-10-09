"""
E0 Formal Run: state-machine runner bridging AGH session ↔ Python registration loop.

Usage (from D:\STUDY\darker\agent-pointcloud-registration):
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' experiments\E0_ablation\run_e0.py --phase 0
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' experiments\E0_ablation\run_e0.py --phase 1 --response-file <path>
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' experiments\E0_ablation\run_e0.py --phase 2 --response-file <path>
  ...

State file: <run_dir>/_state.json
Prompt file: <run_dir>/_prompt.json
Response file: written by AGH session, passed via --response-file
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Setup paths
# ---------------------------------------------------------------------------
BASE = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "src"))

import agent_diagnose
import agent_tools
import agent_probes
import agent_evaluator
import src.agnnes_agent as aa

SOURCE_PLY = str(BASE / "experiments" / "E0_ablation" / "cases" / "scene_01" / "agent_input" / "source_cloud.ply")
TARGET_PLY = str(BASE / "experiments" / "E0_ablation" / "cases" / "scene_01" / "agent_input" / "target_cloud.ply")
GT_NPY     = str(BASE / "experiments" / "E0_ablation" / "cases" / "scene_01" / "evaluator_only" / "gt_transform.npy")
RUN_DIR    = str(BASE / "experiments" / "E0_ablation" / "results" / "e0_scene_01_d_blind04")
RUN_ID     = "e0_scene_01_d_blind04"
MAX_RETRY  = 2

STATE_FILE  = Path(RUN_DIR) / "_state.json"
PROMPT_FILE = Path(RUN_DIR) / "_prompt.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False,
                   default=lambda o: o.item() if isinstance(o, np.generic)
                                     else o.tolist() if isinstance(o, np.ndarray) else str(o)),
        encoding="utf-8")

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def _save_state(state: Dict[str, Any]) -> None:
    _save_json(state, STATE_FILE)

def _load_state() -> Dict[str, Any]:
    return _load_json(STATE_FILE)

def _make_prompt(prompt: str) -> Dict[str, Any]:
    """Write the current prompt to _prompt.json and return a ready-to-print envelope."""
    _save_json({"prompt": prompt, "run_id": RUN_ID, "variant": "REAL_AGNES_ACTIVE_PROBE",
                "scene_id": "scene_01", "seed": "1001"}, PROMPT_FILE)
    return {"prompt_file": str(PROMPT_FILE), "prompt_length_chars": len(prompt)}

# ---------------------------------------------------------------------------
# Phase 0: Diagnosis + initial decision prompt
# ---------------------------------------------------------------------------
def phase_0() -> None:
    Path(RUN_DIR).mkdir(parents=True, exist_ok=True)

    # Diagnosis
    diagnosis = agent_diagnose.diagnose(SOURCE_PLY, TARGET_PLY)
    _save_json(diagnosis, Path(RUN_DIR) / "diagnosis.json")

    input_summary = {
        "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
        "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
        "source_point_count": diagnosis["source_point_count"],
        "target_point_count": diagnosis["target_point_count"],
        "initial_transform_available": diagnosis["initial_transform_available"],
        "note": "Agent decision stage does not access paths or L1/L2/L3/L4 level labels",
    }
    _save_json(input_summary, Path(RUN_DIR) / "input_summary.json")

    # Initial state
    state: Dict[str, Any] = {
        "run_id": RUN_ID,
        "variant": "REAL_AGNES_ACTIVE_PROBE",
        "scene_id": "scene_01",
        "seed": "1001",
        "max_retry": MAX_RETRY,
        "attempts": [],
        "probes_run": [],
        "probe_observations": [],
        "current_step": 1,
        "phase": "decision_01",
        "final_transform": None,
        "final_assessment": None,
        "final_decision": None,
        "done": False,
    }
    _save_state(state)

    # Build decision prompt
    prompt = aa.build_decision_prompt(
        diagnosis,
        agent_tools.TOOL_REGISTRY,
        prior_attempts=[],
        probes_already_run=[],
        probe_observations=[],
    )
    env = _make_prompt(prompt)
    print(json.dumps(env, indent=2))

# ---------------------------------------------------------------------------
# Phase N (N>=1): Process Agnes response, advance state
# ---------------------------------------------------------------------------
def phase_continue(response_path: str) -> None:
    state = _load_state()
    if state.get("done"):
        print(json.dumps({"status": "already_done", "run_dir": RUN_DIR}))
        return

    raw = Path(response_path).read_text(encoding="utf-8")
    phase = state["phase"]
    step = state["current_step"]

    if phase.startswith("decision"):
        _handle_decision_response(raw, state, step)
    elif phase.startswith("assessment"):
        _handle_assessment_response(raw, state, step)
    else:
        raise ValueError(f"Unknown phase: {phase}")

def _handle_decision_response(raw: str, state: Dict[str, Any], step: int) -> None:
    probes_run = state["probes_run"]
    probe_obs = state["probe_observations"]
    attempts = state["attempts"]

    decision = aa.parse_agnnes_decision(raw, probes_already_run=probes_run, probe_observations=probe_obs)
    decision["_agnnes_raw_response"] = raw
    _save_json(decision, Path(RUN_DIR) / f"decision_{step:02d}.json")
    state["final_decision"] = decision

    if "_error" in decision:
        # Guardrail rejected; Agnes must re-select. Save error, build same-step prompt again.
        state["phase"] = f"decision_{step:02d}_error"
        _save_state(state)
        prompt = aa.build_decision_prompt(
            _load_json(Path(RUN_DIR) / "diagnosis.json"),
            agent_tools.TOOL_REGISTRY,
            prior_attempts=attempts,
            probes_already_run=probes_run,
            probe_observations=probe_obs,
        )
        env = _make_prompt(prompt + "\n\n[RETRY REQUIRED] Your previous decision was rejected: " + decision["_error"] + "\nPlease re-submit a corrected decision.")
        print(json.dumps({"status": "decision_rejected", "error": decision["_error"], **env}, indent=2))
        return

    if decision["information_sufficient"]:
        # Proceed to registration
        method = decision["selected_method"]
        policy = decision.get("parameter_policy", {})
        base_scale = float(_load_json(Path(RUN_DIR) / "diagnosis.json").get("base_scale", 0.1))

        obs = agent_tools.dispatch(method, SOURCE_PLY, TARGET_PLY, base_scale=base_scale, param_policy=policy)
        obs_save = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in obs.items()}
        obs_save["tool_name"] = method
        obs_save["parameter_policy_used"] = policy
        _save_json(obs_save, Path(RUN_DIR) / f"observation_{step:02d}.json")

        tool_call = {
            "step": step,
            "tool_name": method,
            "entrypoint": ("src.agent_tools.run_local_icp" if method == "LOCAL_ICP"
                           else "src.agent_tools.run_global_fpfh_ransac_icp"),
            "inputs": {"source": "source_cloud", "target": "target_cloud",
                        "base_scale": base_scale, "parameter_policy": policy},
            "returned_metrics_keys": [k for k in obs_save.keys() if k != "transform"],
            "gt_read": False,
        }
        _save_json(tool_call, Path(RUN_DIR) / f"tool_call_{step:02d}.json")

        state["final_transform"] = obs["transform"].tolist()
        state["phase"] = f"assessment_{step:02d}"
        _save_state(state)

        # Build assessment prompt
        prompt = aa.build_assessment_prompt(
            obs_save, attempts, method, policy,
            probe_observations=probe_obs,
        )
        env = _make_prompt(prompt)
        print(json.dumps({"status": "registration_done", "method": method,
                          "step": step, **env}, indent=2))
    else:
        # Probe requested
        probe_name = decision["requested_probe"]
        base_scale = float(_load_json(Path(RUN_DIR) / "diagnosis.json").get("base_scale", 0.1))
        obs = agent_probes.dispatch_probe(probe_name, SOURCE_PLY, TARGET_PLY, base_scale=base_scale)
        _save_json(obs, Path(RUN_DIR) / f"probe_{step:02d}_{probe_name}.json")
        state["probes_run"].append(probe_name)
        state["probe_observations"].append(obs)
        state["phase"] = f"decision_{step:02d}_probe2"
        _save_state(state)

        # Build next decision prompt (with probe observation)
        prompt = aa.build_decision_prompt(
            _load_json(Path(RUN_DIR) / "diagnosis.json"),
            agent_tools.TOOL_REGISTRY,
            prior_attempts=attempts,
            probes_already_run=state["probes_run"],
            probe_observations=state["probe_observations"],
        )
        env = _make_prompt(prompt)
        print(json.dumps({"status": "probe_done", "probe": probe_name, "step": step, **env}, indent=2))

def _handle_assessment_response(raw: str, state: Dict[str, Any], step: int) -> None:
    obs = _load_json(Path(RUN_DIR) / f"observation_{step:02d}.json")
    method = obs.get("tool_name", "")
    policy = obs.get("parameter_policy_used", {})
    attempts = state["attempts"]

    assessment = aa.parse_agnnes_assessment(raw)
    # Inject fitness for guardrail
    if "fitness" in obs:
        assessment["_fitness"] = obs["fitness"]
    assessment["_agnnes_raw_response"] = raw
    _save_json(assessment, Path(RUN_DIR) / f"agent_assessment_{step:02d}.json")
    state["final_assessment"] = assessment

    # Append to attempts (for next decision round)
    retry_obs = {k: obs.get(k) for k in
                 ("fitness", "rmse", "inlier_rmse", "elapsed_s",
                  "ransac_fitness", "ransac_rmse",
                  "max_correspondence_distance",
                  "ransac_max_correspondence_distance",
                  "icp_max_correspondence_distance") if k in obs}
    attempts.append({
        "step": step,
        "selected_method": method,
        "parameter_policy": policy,
        "observation": retry_obs,
        "assessment": {k: assessment.get(k) for k in
                       ("decision", "reason", "next_method", "next_parameter_policy", "confidence")
                       if k in assessment},
        "decision": assessment["decision"],
    })
    state["attempts"] = attempts

    verdict = assessment["decision"]

    if verdict == "ACCEPT" or verdict == "ABORT":
        _finalize(state)
    else:  # RETRY
        if len(attempts) >= state["max_retry"]:
            # Guardrail: max retries exhausted → force ABORT
            assessment["decision"] = "ABORT"
            assessment["reason"] = "[GUARDRAIL] Max retry limit reached. Forcing ABORT."
            assessment["_guardrail_applied"] = "max_retry_exhausted"
            _save_json(assessment, Path(RUN_DIR) / f"agent_assessment_{step:02d}.json")
            state["final_assessment"] = assessment
            _finalize(state)
        else:
            state["current_step"] = step + 1
            state["phase"] = f"decision_{step + 1:02d}"
            _save_state(state)
            prompt = aa.build_decision_prompt(
                _load_json(Path(RUN_DIR) / "diagnosis.json"),
                agent_tools.TOOL_REGISTRY,
                prior_attempts=attempts,
                probes_already_run=state["probes_run"],
                probe_observations=state["probe_observations"],
            )
            env = _make_prompt(prompt)
            print(json.dumps({"status": "retry", "step": step, "next_step": step + 1, **env}, indent=2))

def _finalize(state: Dict[str, Any]) -> None:
    Path(RUN_DIR).mkdir(parents=True, exist_ok=True)
    final_assessment = state.get("final_assessment")
    final_decision = state.get("final_decision")
    final_transform = state.get("final_transform")

    # Write final assessment & decision files
    if final_assessment:
        _save_json(final_assessment, Path(RUN_DIR) / "agent_final_assessment.json")
    if final_decision:
        _save_json(final_decision, Path(RUN_DIR) / "decision_final.json")

    # Parameters
    diagnosis = _load_json(Path(RUN_DIR) / "diagnosis.json")
    parameters = {
        "base_scale": float(diagnosis.get("base_scale", 0.0)),
        "final_selected_method": (final_decision or {}).get("selected_method"),
        "final_parameter_policy": (final_decision or {}).get("parameter_policy"),
        "note": "Agent-selected scale factors are dimensionless relative to base_scale (diagnosis-derived).",
    }
    _save_json(parameters, Path(RUN_DIR) / "parameters.json")

    # Evaluator (only after terminal verdict - reads GT now)
    if final_transform:
        T_est = np.array(final_transform, dtype=np.float64)
        evaluator_result = agent_evaluator.evaluate_agent_result(T_est, GT_NPY)
        agent_evaluator.save_evaluator_result(evaluator_result, str(Path(RUN_DIR) / "evaluator_result.json"))
    else:
        evaluator_result = {
            "gt_evaluator": True,
            "note": "No transform produced (ABORT before registration)",
            "success": False,
            "rot_err_deg": None,
            "trans_err": None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        }
        _save_json(evaluator_result, Path(RUN_DIR) / "evaluator_result.json")

    # AGH log
    agh_log = {
        "agent_model_name": "agnes-3.0-flash",
        "agent_model_version": "2026-10-06",
        "decision_implementation": "agnnes_real",
        "variant": "REAL_AGNES_ACTIVE_PROBE",
        "scene_id": "scene_01",
        "seed": "1001",
        "run_id": RUN_ID,
        "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "attempts": len(state.get("attempts", [])),
        "probes_executed": state.get("probes_run", []),
        "final_verdict": (final_assessment or {}).get("decision"),
        "gt_success": evaluator_result.get("success"),
        "gt_rot_err_deg": evaluator_result.get("rot_err_deg"),
        "gt_trans_err": evaluator_result.get("trans_err"),
        "tool_calls": [f"tool_call_{a['step']:02d}.json" for a in state.get("attempts", [])],
        "decisions": [f"decision_{i:02d}.json" for i in range(1, len(state.get("attempts", [])) + 1)],
        "assessments": [f"agent_assessment_{i:02d}.json" for i in range(1, len(state.get("attempts", [])) + 1)],
        "probe_files": [f"probe_{i:02d}_{p}.json" for i, p in enumerate(state.get("probes_run", []), 1)],
    }
    _save_json(agh_log, Path(RUN_DIR) / "agh_run_log.json")

    state["done"] = True
    _save_state(state)

    print(json.dumps({
        "status": "complete",
        "run_id": RUN_ID,
        "final_verdict": (final_assessment or {}).get("decision"),
        "gt_success": evaluator_result.get("success"),
        "gt_rot_err_deg": evaluator_result.get("rot_err_deg"),
        "gt_trans_err": evaluator_result.get("trans_err"),
        "attempts": len(state.get("attempts", [])),
        "probes": state.get("probes_run", []),
        "run_dir": RUN_DIR,
    }, indent=2))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, required=True)
    ap.add_argument("--response-file", default=None)
    args = ap.parse_args()

    if args.phase == 0:
        phase_0()
    else:
        if not args.response_file:
            raise SystemExit("--response-file required for phase >= 1")
        phase_continue(args.response_file)

if __name__ == "__main__":
    main()
