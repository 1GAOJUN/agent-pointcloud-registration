"""B3A：解析 Agnes 原始决策 + 执行 Probe + 保存结果。

用法：
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_b3a_execute_probe.py <round_no>

round_no = 对应 agnnes_raw_decision_NN.json 的轮次号（1/2/3）
- 读取 agnnes_raw_decision_NN.json
- 运行 guardrail 校验
- 若 requested_probe 非 NONE → 执行 Probe → 写 probe_observation_NN.json
- 若 information_sufficient=true → 打印 final method+policy
- 若配额耗尽且 Agnes 仍请求 Probe → 终止并写 stop_report
"""
import sys, json, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose
from agent_probes import (
    PROBE_DISPATCH, MAX_PROBES_PER_RUN,
    run_pca_orientation_probe, run_cheap_local_icp_probe,
)
import agnnes_agent

case = ROOT / "data" / "L1" / "seed_101"
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"
agent_dir = run_dir / "02_AGENT"

round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
raw_path = run_dir / "01_AGH" / f"agnnes_raw_decision_{round_no:02d}.json"
raw = raw_path.read_text(encoding="utf-8")

# 读取已有 Probe 观测（index < round_no）
probes_run: list[str] = []
probe_obs: list[dict] = []
for i in range(1, round_no):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs = json.loads(p.read_text(encoding="utf-8"))
        probe_obs.append(obs)
        probes_run.append(obs.get("_probe_request", {}).get("probe_name") or obs.get("probe_name"))

diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8"))
base_scale = float(diagnosis.get("base_scale", 0.1))

decision = agnnes_agent.parse_agnnes_decision(raw, probes_already_run=probes_run, probe_observations=probe_obs)
parsed_path = agent_dir / f"agnnes_decision_{round_no:02d}_parsed.json"
with open(parsed_path, "w", encoding="utf-8") as f:
    json.dump(decision, f, indent=2, ensure_ascii=False, default=str)

if "_error" in decision:
    print(f"[ERROR] round {round_no} guardrail: {decision['_error']}")
    sys.exit(2)

print(f"[round {round_no}] sufficient={decision['information_sufficient']} "
      f"requested_probe={decision.get('requested_probe')} "
      f"selected_method={decision.get('selected_method')} "
      f"confidence={decision.get('confidence')}")

if decision["information_sufficient"]:
    # Agnes 决定正式方法
    print(f"[FINAL] method={decision['selected_method']} policy={decision.get('parameter_policy')}")
    sys.exit(0)

probe_name = decision["requested_probe"]
if probe_name not in PROBE_DISPATCH:
    print(f"[ERROR] invalid probe '{probe_name}'"); sys.exit(3)
if probe_name in probes_run:
    print(f"[ERROR] duplicate probe '{probe_name}' blocked"); sys.exit(3)
if len(probes_run) >= MAX_PROBES_PER_RUN:
    print(f"[ERROR] quota ({MAX_PROBES_PER_RUN}) exhausted; "
          f"Agnes must select formal method next round")
    sys.exit(4)

t0 = time.time()
if probe_name == "PCA_ORIENTATION":
    obs = run_pca_orientation_probe(str(case / "source.ply"), str(case / "target.ply"))
else:
    obs = run_cheap_local_icp_probe(str(case / "source.ply"), str(case / "target.ply"),
                                      base_scale=base_scale)
obs["_probe_request"] = {
    "probe_name": probe_name,
    "requested_by": "agnnes_real",
    "probe_reason": decision.get("probe_reason"),
    "round": round_no,
}
obs_path = agent_dir / f"probe_observation_{len(probes_run)+1:02d}.json"
with open(obs_path, "w", encoding="utf-8") as f:
    json.dump(obs, f, indent=2, ensure_ascii=False, default=str)
print(f"[PROBE] {probe_name} -> {obs_path.name}  ({time.time()-t0:.3f}s)")
print(json.dumps({k: v for k, v in obs.items() if k != "_probe_request"},
                 indent=2, ensure_ascii=False, default=str))
