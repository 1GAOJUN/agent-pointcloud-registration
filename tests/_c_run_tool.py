"""Phase C: Parse final Agnes decision (round N) + run guardrails + execute registration tool.

Usage:
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_c_run_tool.py <round_no> <attempt_no>

Reads 01_AGH/agnnes_raw_decision_NN.json (the round where information_sufficient=true).
Writes observation / tool_call / parameters / metrics for attempt <attempt_no>.
GT is NOT read.
"""
import sys, json, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_tools import run_local_icp, run_global_fpfh_ransac_icp
import agnnes_agent

case = ROOT / "data" / "formal_blind" / "case_unknown_C_20261008_s707"
source_ply = str(case / "agent_input" / "source_cloud.ply")
target_ply = str(case / "agent_input" / "target_cloud.ply")
run_dir = ROOT / "outputs" / "submission_evidence" / "C" / "runs" / "c_unknown_20261008_s707_blind01"
agent_dir = run_dir / "02_AGENT"
attempt_no = int(sys.argv[2]) if len(sys.argv) > 2 else 1
attempt_dir = run_dir / "attempts" / f"attempt_{attempt_no:02d}"
attempt_dir.mkdir(parents=True, exist_ok=True)

round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
raw = (run_dir / "01_AGH" / f"agnnes_raw_decision_{round_no:02d}.json").read_text(encoding="utf-8-sig")
try:
    _envelope = json.loads(raw)
    if isinstance(_envelope, dict) and "text_payload" in _envelope and str(_envelope.get("invocation", "")).startswith("agh"):
        raw = _envelope["text_payload"]
except (json.JSONDecodeError, TypeError):
    pass

probes_run = []
probe_obs = []
for i in range(1, round_no):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs = json.loads(p.read_text(encoding="utf-8-sig"))
        probe_obs.append(obs)
        probes_run.append(obs.get("_probe_request", {}).get("probe_name") or obs.get("probe_name"))

decision = agnnes_agent.parse_agnnes_decision(raw, probes_already_run=probes_run, probe_observations=probe_obs)
with open(agent_dir / f"agnnes_decision_{round_no:02d}_parsed.json", "w", encoding="utf-8") as f:
    json.dump(decision, f, indent=2, ensure_ascii=False, default=str)

if "_error" in decision:
    print(f"[ERROR] round {round_no} guardrail: {decision['_error']}")
    sys.exit(2)

if not decision.get("information_sufficient"):
    print("[ERROR] this round must set information_sufficient=true (quota exhausted / RETRY re-decision)")
    sys.exit(2)

method = decision["selected_method"]
policy = decision.get("parameter_policy", {})
diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8-sig"))
base_scale = float(diagnosis.get("base_scale", 0.1))

if attempt_no == 1:
    with open(agent_dir / "decision_final.json", "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2, ensure_ascii=False, default=str)

print(f"[FINAL attempt {attempt_no}] method={method} policy={policy} base_scale={base_scale:.6f}")

t0 = time.perf_counter()
if method == "LOCAL_ICP":
    obs = run_local_icp(source_ply, target_ply,
                        icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
                        base_scale=base_scale)
elif method == "GLOBAL_FPFH_RANSAC_ICP":
    obs = run_global_fpfh_ransac_icp(
        source_ply, target_ply,
        global_corr_scale=policy.get("global_corr_scale", 4.0),
        icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
        base_scale=base_scale)
else:
    print(f"[ERROR] unknown method: {method}"); sys.exit(5)
tool_elapsed = time.perf_counter() - t0

import numpy as np
obs_save = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in obs.items()}
obs_save["tool_name"] = method
obs_save["parameter_policy_used"] = policy
obs_save["tool_elapsed_s"] = round(tool_elapsed, 4)

for d in (agent_dir, attempt_dir):
    with open(d / f"observation_{attempt_no:02d}.json", "w", encoding="utf-8") as f:
        json.dump(obs_save, f, indent=2, ensure_ascii=False, default=str)

tool_call = {
    "step": attempt_no,
    "tool_name": method,
    "entrypoint": ("src.agent_tools.run_local_icp" if method == "LOCAL_ICP"
                   else "src.agent_tools.run_global_fpfh_ransac_icp"),
    "inputs": {
        "source": "source_cloud (path withheld from Agent)",
        "target": "target_cloud (path withheld from Agent)",
        "base_scale": base_scale,
        "parameter_policy": policy,
    },
    "derived_actual_parameters": {
        "icp_max_corr_scale_agies": policy.get("icp_max_corr_scale"),
        "global_corr_scale_agies": policy.get("global_corr_scale"),
        "icp_max_correspondence_distance": round(max(1e-4, base_scale * float(policy.get("icp_max_corr_scale", 1.0))), 6),
        "ransac_max_correspondence_distance": (
            round(max(1e-3, base_scale * float(policy.get("global_corr_scale", 4.0))), 6)
            if method == "GLOBAL_FPFH_RANSAC_ICP" else None
        ),
    },
    "returned_metrics_keys": list(obs_save.keys()),
    "gt_read": False,
    "wall_time_s": round(tool_elapsed, 4),
}
with open(run_dir / "03_TOOL_CHAIN" / f"tool_call_{attempt_no:02d}.json", "w", encoding="utf-8") as f:
    json.dump(tool_call, f, indent=2, ensure_ascii=False, default=str)

params = {
    "base_scale": base_scale,
    "agnnes_multiplier": policy,
    "derived_actual_parameters": tool_call["derived_actual_parameters"],
    "final_selected_method": method,
    "note": "Agent chooses multiplier; Python computes actual distances. No fallback to fixed values.",
}
with open(run_dir / "04_CONFIG" / f"parameters_attempt_{attempt_no:02d}.json", "w", encoding="utf-8") as f:
    json.dump(params, f, indent=2, ensure_ascii=False, default=str)

metrics = {k: obs_save.get(k) for k in (
    "fitness", "rmse", "inlier_rmse", "ransac_fitness", "ransac_rmse",
    "elapsed_s", "max_correspondence_distance",
    "ransac_max_correspondence_distance", "icp_max_correspondence_distance",
    "tool_name")}
for d in (agent_dir, attempt_dir):
    with open(d / f"metrics_attempt_{attempt_no:02d}.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
print("[done] observation + tool_call + params + metrics saved for attempt", attempt_no)
