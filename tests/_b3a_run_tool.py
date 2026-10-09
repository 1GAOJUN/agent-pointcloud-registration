"""B3A：解析第3轮决策 + 执行正式 Registration 工具 + 保存 observation。

- 验证 agnnes_raw_decision_03.json 通过 guardrail
- 按 selected_method + parameter_policy 执行正式工具
- 保存 observation_01.json / tool_call_01.json 到 02_AGENT/
- 保存 tool_call 到 03_TOOL_CHAIN/
"""
import sys, json, time
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_tools import run_local_icp, run_global_fpfh_ransac_icp
import agnnes_agent

case = ROOT / "data" / "L1" / "seed_101"
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"
agent_dir = run_dir / "02_AGENT"

raw3 = (run_dir / "01_AGH" / "agnnes_raw_decision_03.json").read_text(encoding="utf-8")
probes_run = ["PCA_ORIENTATION", "CHEAP_LOCAL_ICP"]
probe_obs = []
for i in (1, 2):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        probe_obs.append(json.loads(p.read_text(encoding="utf-8")))

decision = agnnes_agent.parse_agnnes_decision(raw3, probes_already_run=probes_run, probe_observations=probe_obs)
with open(agent_dir / "agnnes_decision_03_parsed.json", "w", encoding="utf-8") as f:
    json.dump(decision, f, indent=2, ensure_ascii=False, default=str)

if "_error" in decision:
    print(f"[ERROR] decision 03 guardrail: {decision['_error']}"); sys.exit(2)

method = decision["selected_method"]
policy = decision.get("parameter_policy", {})
diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8"))
base_scale = float(diagnosis.get("base_scale", 0.1))

# 保存 decision_final.json
with open(agent_dir / "decision_final.json", "w", encoding="utf-8") as f:
    json.dump(decision, f, indent=2, ensure_ascii=False, default=str)

print(f"[FINAL] method={method} policy={policy} base_scale={base_scale:.6f}")

# 执行正式工具
t0 = time.perf_counter()
if method == "LOCAL_ICP":
    obs = run_local_icp(str(case / "source.ply"), str(case / "target.ply"),
                        icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
                        base_scale=base_scale)
elif method == "GLOBAL_FPFH_RANSAC_ICP":
    obs = run_global_fpfh_ransac_icp(
        str(case / "source.ply"), str(case / "target.ply"),
        global_corr_scale=policy.get("global_corr_scale", 5.0),
        icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
        base_scale=base_scale)
else:
    print(f"[ERROR] unknown method: {method}"); sys.exit(5)
tool_elapsed = time.perf_counter() - t0

obs_save = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in obs.items()}
obs_save["tool_name"] = method
obs_save["parameter_policy_used"] = policy
obs_save["tool_elapsed_s"] = round(tool_elapsed, 4)

with open(agent_dir / "observation_01.json", "w", encoding="utf-8") as f:
    json.dump(obs_save, f, indent=2, ensure_ascii=False, default=str)

# 03_TOOL_CHAIN/tool_call_01.json
tool_call = {
    "step": 1,
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
        "max_correspondence_distance": (
            round(max(1e-4, base_scale * float(policy.get("icp_max_corr_scale", 1.0))), 6)
            if method == "LOCAL_ICP"
            else None
        ),
        "ransac_max_corr": (
            round(max(1e-3, base_scale * float(policy.get("global_corr_scale", 5.0))), 6)
            if method == "GLOBAL_FPFH_RANSAC_ICP"
            else None
        ),
    },
    "returned_metrics_keys": list(obs_save.keys()),
    "gt_read": False,
    "wall_time_s": round(tool_elapsed, 4),
}
with open(run_dir / "03_TOOL_CHAIN" / "tool_call_01.json", "w", encoding="utf-8") as f:
    json.dump(tool_call, f, indent=2, ensure_ascii=False, default=str)

# 保存 parameters.json
params = {
    "base_scale": base_scale,
    "agnnes_multiplier": policy,
    "derived_actual_parameters": tool_call["derived_actual_parameters"],
    "final_selected_method": method,
    "note": "Agent chooses multiplier; Python computes actual distances.",
}
with open(run_dir / "04_CONFIG" / "parameters.json", "w", encoding="utf-8") as f:
    json.dump(params, f, indent=2, ensure_ascii=False, default=str)

# 保存 metrics.json
metrics = {
    "fitness": obs_save.get("fitness"),
    "rmse": obs_save.get("rmse"),
    "inlier_rmse": obs_save.get("inlier_rmse"),
    "ransac_fitness": obs_save.get("ransac_fitness"),
    "ransac_rmse": obs_save.get("ransac_rmse"),
    "elapsed_s": obs_save.get("elapsed_s"),
    "max_correspondence_distance": obs_save.get("max_correspondence_distance"),
    "ransac_max_correspondence_distance": obs_save.get("ransac_max_correspondence_distance"),
    "icp_max_correspondence_distance": obs_save.get("icp_max_correspondence_distance"),
    "tool_name": method,
}
with open(agent_dir / "metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
print(f"[done] observation + tool_call + params + metrics saved")
