"""B3A：生成发送给 Agnes 的 decision prompt（第 N 轮）。

用法（从项目根目录）：
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_b3a_decision_prompt.py <round_no>

  round_no=1: 无 Probe 观测
  round_no=2: 已读 probe_observation_01.json
  round_no=3: 已读 probe_observation_01/02.json

输出：
  01_AGH/agnnes_decision_prompt_NN.json
  同时打印 prompt 全文到 stdout（供 subagent_fork 使用）
"""
import sys, json
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY
import agnnes_agent

case = ROOT / "data" / "L1" / "seed_101"
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"
agent_dir = run_dir / "02_AGENT"

round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1

diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8"))

# 读取已有 Probe 观测（index < round_no）
probes_run: list[str] = []
probe_obs: list[dict] = []
for i in range(1, round_no):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs = json.loads(p.read_text(encoding="utf-8"))
        probe_obs.append(obs)
        probes_run.append(obs.get("_probe_request", {}).get("probe_name") or obs.get("probe_name"))

prompt = agnnes_agent.build_decision_prompt(
    diagnosis, TOOL_REGISTRY, [],
    probes_already_run=probes_run, probe_observations=probe_obs)

out = run_dir / "01_AGH" / f"agnnes_decision_prompt_{round_no:02d}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"prompt": json.loads(prompt),
                           "meta": {"round": round_no, "probes_already_run": probes_run}},
                          indent=2, ensure_ascii=False, default=str), encoding="utf-8")

print(f"[OK] prompt round={round_no} probes_already_run={probes_run}")
print("--- PROMPT JSON (for subagent_fork) ---")
print(prompt)
