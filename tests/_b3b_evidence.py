"""B3B: build standard evidence files for the run (post-core-freeze).

Generates:
  05_VALIDATION/metrics_summary.json
  05_VALIDATION/TOOL_CHAIN.md
  05_VALIDATION/run_summary.md
  00_INDEX/run_manifest.json
  attempts/attempt_01/ (already has its copies; this adds run_manifest at root 00_INDEX)
"""
import json, sys, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
agent_dir = run_dir / "02_AGENT"
val_dir = run_dir / "05_VALIDATION"

diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8-sig"))
obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8-sig"))
evalr = json.loads((val_dir / "evaluator_result.json").read_text(encoding="utf-8-sig"))
final_assess = json.loads((agent_dir / "agent_final_assessment.json").read_text(encoding="utf-8-sig"))
params = json.loads((run_dir / "04_CONFIG" / "parameters.json").read_text(encoding="utf-8-sig"))
tool_call = json.loads((run_dir / "03_TOOL_CHAIN" / "tool_call_01.json").read_text(encoding="utf-8-sig"))

# metrics_summary.json — clearly separates Agent-observable metrics from GT evaluation
metrics_summary = {
    "run_id": "b3_l2_20261007_seed202_blind01",
    "agent_observable_metrics": {
        "fitness": obs.get("fitness"),
        "rmse": obs.get("rmse"),
        "ransac_fitness": obs.get("ransac_fitness"),
        "ransac_rmse": obs.get("ransac_rmse"),
        "elapsed_s": obs.get("elapsed_s"),
        "tool_name": obs.get("tool_name"),
    },
    "independent_gt_evaluation": {
        "rotation_error_deg": evalr.get("rot_err_deg"),
        "translation_error": evalr.get("trans_err"),
        "success": evalr.get("success"),
        "rot_thr_deg": evalr.get("rot_thr_deg"),
        "trans_thr": evalr.get("trans_thr"),
    },
    "probe_observations": [
        {
            "probe_name": "PCA_ORIENTATION",
            "rotation_estimate_deg": json.loads((agent_dir / "probe_observation_01.json").read_text(encoding="utf-8-sig")).get("rotation_estimate_deg"),
            "orientation_confidence": json.loads((agent_dir / "probe_observation_01.json").read_text(encoding="utf-8-sig")).get("orientation_confidence"),
        },
        {
            "probe_name": "CHEAP_LOCAL_ICP",
            "initial_fitness": json.loads((agent_dir / "probe_observation_02.json").read_text(encoding="utf-8-sig")).get("initial_fitness"),
            "probe_fitness": json.loads((agent_dir / "probe_observation_02.json").read_text(encoding="utf-8-sig")).get("probe_fitness"),
        },
    ],
    "final_agent_decision": final_assess.get("decision"),
    "attempt_count": 1,
    "retried": False,
}
val_dir.joinpath("metrics_summary.json").write_text(json.dumps(metrics_summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print("[ok] 05_VALIDATION/metrics_summary.json")

# run_manifest.json (at 00_INDEX)
run_manifest = {
    "run_id": "b3_l2_20261007_seed202_blind01",
    "phase": "B3B",
    "anonymous_case_label": "case_unknown_B",
    "data_path_hidden_from_agent": "outputs/ICP/L2/L2/seed_202 (Python-only)",
    "python_executable": "D:\\APP\\Anaconda\\envs\\pointcloud_agh\\python.exe",
    "python_version": "3.11.16",
    "open3d_version": "0.20.0",
    "selected_method": obs.get("tool_name"),
    "parameter_policy_agies": params.get("agnnes_multiplier"),
    "derived_actual_parameters": params.get("derived_actual_parameters"),
    "final_agent_decision": final_assess.get("decision"),
    "gt_success": evalr.get("success"),
    "gt_rotation_error_deg": evalr.get("rot_err_deg"),
    "gt_translation_error": evalr.get("trans_err"),
    "fitness": obs.get("fitness"),
    "rmse": obs.get("rmse"),
    "runtime_s": obs.get("elapsed_s"),
    "probe_chain": ["PCA_ORIENTATION", "CHEAP_LOCAL_ICP"],
    "attempts": ["attempt_01"],
    "retry_occurred": False,
    "evidence_dir": str(run_dir),
    "core_frozen_file": "00_INDEX/B3B_CORE_FROZEN.md",
    "created_at_utc": "2026-10-07",
}
(run_dir / "00_INDEX" / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print("[ok] 00_INDEX/run_manifest.json")

# TOOL_CHAIN.md
tool_chain_md = f"""# TOOL_CHAIN — b3_l2_20261007_seed202_blind01

## Registered Algorithm Tools

| Tool | Entrypoint | When used |
|------|-----------|-----------|
| LOCAL_ICP | `src.agent_tools.run_local_icp` | Not used in this run |
| GLOBAL_FPFH_RANSAC_ICP | `src.agent_tools.run_global_fpfh_ransac_icp` | **Used in this run** (Agnes round-3 selection) |

## Probe Tools (observational, never auto-select)

| Probe | Entrypoint | Used |
|-------|-----------|------|
| PCA_ORIENTATION | `src.agent_probes.run_pca_orientation_probe` | Yes (Agnes round-1 request) |
| CHEAP_LOCAL_ICP | `src.agent_probes.run_cheap_local_icp_probe` | Yes (Agnes round-2 request) |

## Execution Trace

1. `diagnose(source.ply, target.ply)` → `diagnosis.json`
2. Agnes decision round 1 → `information_sufficient=false`, `requested_probe=PCA_ORIENTATION`
3. `run_pca_orientation_probe` → `probe_observation_01.json` (LOW, null rotation)
4. Agnes decision round 2 → `information_sufficient=false`, `requested_probe=CHEAP_LOCAL_ICP`
5. `run_cheap_local_icp_probe` → `probe_observation_02.json` (weak improvement)
6. Agnes decision round 3 (quota exhausted) → `selected_method=GLOBAL_FPFH_RANSAC_ICP`,
   `parameter_policy: global_corr_scale=4.0, icp_max_corr_scale=1.0`
7. `run_global_fpfh_ransac_icp` with derived actual parameters → `observation_01.json`
   (fitness=1.0, rmse≈1.6e-16)
8. Agnes assessment → `ACCEPT` (confidence 0.97, no guardrail overwrite)
9. `evaluate_agent_result` (GT read here only) → `evaluator_result.json`
   (rot_err=0.0, trans_err=0.0, success=true)

## Parameter Derivation

- base_scale = {diagnosis.get('base_scale'):.6f}
- Agnes multiplier: global_corr_scale=4.0, icp_max_corr_scale=1.0
- Actual ransac_max_correspondence_distance = {params.get('derived_actual_parameters', dict()).get('ransac_max_correspondence_distance')}
- Actual icp_max_correspondence_distance = {params.get('derived_actual_parameters', dict()).get('icp_max_correspondence_distance')}
"""
(run_dir / "03_TOOL_CHAIN" / "TOOL_CHAIN.md").write_text(tool_chain_md, encoding="utf-8")
print("[ok] 03_TOOL_CHAIN/TOOL_CHAIN.md")

# run_summary.md
run_summary_md = f"""# Run Summary — b3_l2_20261007_seed202_blind01 (B3B)

## Case
- Anonymous label: **case_unknown_B**
- Data: seed_202 L2 historical data (path withheld from Agnes)
- Source/target: 30,000 points each, density ratio ≈ 1.0, centroid distance ≈ 0.559

## Agent Behavior
- **Probe chain (Agnes-chosen order):** PCA_ORIENTATION → CHEAP_LOCAL_ICP
- **PCA observation:** `rotation_estimate_deg=null`, `orientation_confidence=LOW`
  (near_line_degeneracy on both clouds — shape is roughly cylindrical/rod-like,
  transverse axes ambiguous; PCA correctly refused to emit an angle)
- **Cheap ICP probe observation:** fitness 0.137 → 0.165 after 5 identity-init
  iterations; weak improvement signals poor local basin
- **Formal method (Agnes round 3):** `GLOBAL_FPFH_RANSAC_ICP`
- **Parameter policy (Agnes):** `global_corr_scale=4.0, icp_max_corr_scale=1.0`
- **Agent final decision:** `ACCEPT` (confidence 0.97)
- **Retries:** none (1 attempt only)

## Agent-Observable Result
- fitness = 1.0
- rmse ≈ 1.63e-16
- ransac_fitness = 1.0
- runtime = 0.582 s

## Independent GT Evaluation (post-Agent-stop only)
- rotation_error_deg = **0.0**
- translation_error = **0.0**
- success = **true**

## Final Status
**PASS** (GT success=true, Agent ACCEPT, no RETRY, no leakage detected in
audit — see 05_VALIDATION/B3B_VALIDATION.md).
"""
val_dir.joinpath("run_summary.md").write_text(run_summary_md, encoding="utf-8")
print("[ok] 05_VALIDATION/run_summary.md")
