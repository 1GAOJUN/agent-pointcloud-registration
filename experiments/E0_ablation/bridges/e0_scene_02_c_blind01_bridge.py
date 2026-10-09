"""E0 REAL_AGNES_NO_PROBE bridge for e0_scene_02_c_blind01.

Wires src.agent_runner.run_agent_case with AgnesDecisionAdapter using
subagent_fork as the AGH raw-response layer. Active Probe disabled (NONE).

Run:
    python experiments/E0_ablation/bridges/e0_scene_02_c_blind01_bridge.py

All files written under:
    D:\STUDY\darker\agent-pointcloud-registration\experiments\E0_ablation\results\e0_scene_02_c_blind01
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_PLY  = str(PROJECT_ROOT / "experiments/E0_ablation/cases/scene_02/agent_input/source_cloud.ply")
TARGET_PLY  = str(PROJECT_ROOT / "experiments/E0_ablation/cases/scene_02/agent_input/target_cloud.ply")
GT_NPY      = str(PROJECT_ROOT / "experiments/E0_ablation/cases/scene_02/evaluator_only/gt_transform.npy")
OUT_DIR     = str(PROJECT_ROOT / "experiments/E0_ablation/results/e0_scene_02_c_blind01")

DECISION_PROMPT_INSTRUCTION = """You are Agnes, a 3D point cloud registration agent.
Read the JSON input below, produce ONLY a valid JSON object matching the output_schema.
Do not add any prose before or after the JSON. Do not read GT or scene labels.
"""

ASSESSMENT_PROMPT_INSTRUCTION = """You are Agnes, a 3D point cloud registration agent.
Read the JSON input below, produce ONLY a valid JSON object matching the output_schema.
Do not add any prose before or after the JSON. Do not read GT transform or error values.
"""


def _make_raw_fn(prompt_instruction: str):
    """Return a callable that will be used as get_raw_decision / get_raw_assessment.
    Since subagent_fork is called OUTSIDE Python, we write the prompt to a file
    and read back the response file. The AGH orchestrator (this session) calls
    subagent_fork between the two Python phases.
    """
    import uuid
    def _fn(prompt: str) -> str:
        # Write prompt, signal AGH orchestrator to call subagent_fork,
        # read response. For a single-process bridge we use file-based handoff.
        import os
        tag = uuid.uuid4().hex[:8]
        prompt_file = Path(OUT_DIR) / f"_prompt_{tag}.json"
        response_file = Path(OUT_DIR) / f"_response_{tag}.txt"
        prompt_file.write_text(prompt_instruction + prompt, encoding="utf-8")
        # Write a control file that the AGH orchestrator watches
        ctrl = Path(OUT_DIR) / f"_ctrl_{tag}.json"
        ctrl.write_text(json.dumps({"prompt_file": str(prompt_file),
                                     "response_file": str(response_file),
                                     "instruction": prompt_instruction}), encoding="utf-8")
        # Wait for orchestrator to write response (blocking read)
        import time
        timeout = 300
        elapsed = 0
        while not response_file.exists():
            time.sleep(2)
            elapsed += 2
            if elapsed > timeout:
                raise TimeoutError(f"Agnes response not received within {timeout}s")
        return response_file.read_text(encoding="utf-8")
    return _fn


def main() -> None:
    import src.agent_runner as runner
    import src.agnnes_agent as ag

    out_p = Path(OUT_DIR)
    out_p.mkdir(parents=True, exist_ok=True)

    # Phase 1: write diagnosis + control files so AGH orchestrator can call subagent_fork
    diagnosis = runner.diagnose(SOURCE_PLY, TARGET_PLY)
    runner._write_json(diagnosis, out_p / "diagnosis.json")

    # Build the full decision prompt
    tools = runner.TOOL_REGISTRY
    prompt_decide = ag.build_decision_prompt(diagnosis, tools, [])
    ctrl_decide_file = out_p / "_ctrl_decision.json"
    ctrl_decide_file.write_text(json.dumps({
        "phase": "decide",
        "prompt": DECISION_PROMPT_INSTRUCTION + prompt_decide,
        "response_file": str(out_p / "_response_decision.txt"),
    }), encoding="utf-8")

    print("PHASE1_READY")
    print("decision_prompt_file:", ctrl_decide_file)
    print("diagnosis:", json.dumps(diagnosis, ensure_ascii=False, default=str)[:500])

    # Phase 2: wait for AGH orchestrator to call subagent_fork and write response
    import time
    resp_decide_file = out_p / "_response_decision.txt"
    timeout = 300
    elapsed = 0
    while not resp_decide_file.exists():
        time.sleep(3)
        elapsed += 3
        if elapsed > timeout:
            raise TimeoutError("Agnes decision response not received")

    raw_decision = resp_decide_file.read_text(encoding="utf-8")
    decision = ag.parse_agnnes_decision(raw_decision)
    runner._write_json(decision, out_p / "decision_01.json")

    if decision.get("_error"):
        print("DECISION_ERROR:", decision["_error"])
        sys.exit(1)

    # Execute tool
    method = decision["selected_method"]
    policy = decision.get("parameter_policy", {})
    base_scale = float(diagnosis.get("base_scale", 0.1))

    if method == "LOCAL_ICP":
        obs = runner.run_local_icp(SOURCE_PLY, TARGET_PLY,
                                   icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
                                   base_scale=base_scale)
    elif method == "GLOBAL_FPFH_RANSAC_ICP":
        obs = runner.run_global_fpfh_ransac_icp(
            SOURCE_PLY, TARGET_PLY,
            global_corr_scale=policy.get("global_corr_scale", 5.0),
            icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
            base_scale=base_scale)
    else:
        raise ValueError(f"Invalid method: {method}")

    import numpy as np
    obs_save = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in obs.items()}
    obs_save["tool_name"] = method
    obs_save["parameter_policy_used"] = policy
    runner._write_json(obs_save, out_p / "observation_01.json")

    tool_call = {
        "step": 1, "tool_name": method,
        "entrypoint": ("src.agent_tools.run_local_icp" if method == "LOCAL_ICP"
                       else "src.agent_tools.run_global_fpfh_ransac_icp"),
        "inputs": {"source": "source_cloud", "target": "target_cloud",
                   "base_scale": base_scale, "parameter_policy": policy},
        "returned_metrics_keys": list(obs_save.keys()),
        "gt_read": False,
    }
    runner._write_json(tool_call, out_p / "tool_call_01.json")

    # Build assessment prompt
    prompt_assess = ag.build_assessment_prompt(obs_save, [], method, policy)
    ctrl_assess_file = out_p / "_ctrl_assessment.json"
    ctrl_assess_file.write_text(json.dumps({
        "phase": "assess",
        "prompt": ASSESSMENT_PROMPT_INSTRUCTION + prompt_assess,
        "response_file": str(out_p / "_response_assessment.txt"),
    }), encoding="utf-8")

    print("PHASE2_READY")
    print("assessment_prompt_file:", ctrl_assess_file)
    print("observation_keys:", [k for k in obs_save.keys() if k not in ("transform",)])

    # Phase 3: wait for AGH orchestrator to write assessment response
    resp_assess_file = out_p / "_response_assessment.txt"
    elapsed = 0
    timeout = 300
    while not resp_assess_file.exists():
        time.sleep(3)
        elapsed += 3
        if elapsed > timeout:
            raise TimeoutError("Agnes assessment response not received")

    raw_assessment = resp_assess_file.read_text(encoding="utf-8")
    assessment = ag.agnnes_assess_from_raw(obs_save, [], method, policy, raw_assessment)
    runner._write_json(assessment, out_p / "agent_assessment_01.json")

    if assessment.get("_error"):
        print("ASSESSMENT_ERROR:", assessment["_error"])
        sys.exit(1)

    # Write final outputs
    runner._write_json(assessment, out_p / "agent_final_assessment.json")
    runner._write_json(decision, out_p / "decision_final.json")
    runner._write_json({
        "base_scale": base_scale,
        "final_selected_method": method,
        "final_parameter_policy": policy,
        "note": "Agent 选择的是相对诊断尺度的倍率档位，非绝对值。",
    }, out_p / "parameters.json")

    # Evaluator (GT read only after Agent terminal verdict)
    evaluator_result = runner.evaluate_agent_result(obs["transform"], GT_NPY)
    runner.save_evaluator_result(evaluator_result, str(out_p / "evaluator_result.json"))

    agh_log = {
        "agent_model_name": "agnes-3.0-flash",
        "agent_model_version": "2026-10-06",
        "decision_implementation": "agnnes_real",
        "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "requested_probe": "NONE",
        "tool_calls": ["tool_call_01.json"],
        "decisions": ["decision_01.json"],
        "assessments": ["agent_assessment_01.json"],
        "note": "REAL_AGNES_NO_PROBE: Agnes decision/assessment via AGH subagent_fork. Probe disabled.",
    }
    runner._write_json(agh_log, out_p / "agh_run_log.json")

    input_summary = {
        "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
        "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
        "source_point_count": diagnosis["source_point_count"],
        "target_point_count": diagnosis["target_point_count"],
        "initial_transform_available": diagnosis["initial_transform_available"],
        "note": "Agent 决策阶段不接收完整路径或 L1/L2/L3/L4 场景标签。",
    }
    runner._write_json(input_summary, out_p / "input_summary.json")

    print("DONE")
    print(json.dumps({
        "run_id": "e0_scene_02_c_blind01",
        "attempts": 1,
        "method": method,
        "final_decision": assessment["decision"],
        "gt_success": evaluator_result["success"],
        "gt_rot_err_deg": evaluator_result["rot_err_deg"],
        "gt_trans_err": evaluator_result["trans_err"],
        "out_dir": OUT_DIR,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
