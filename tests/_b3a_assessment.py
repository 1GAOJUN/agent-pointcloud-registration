"""B3A：生成 Agnes assessment prompt + 执行 assessment。

- 读取 observation_01.json + probe_obs
- 构造 assessment prompt → 01_AGH/agnnes_assessment_prompt.json
- AGH session 读 agnnes_raw_assessment.json → 解析 + guardrail
- 写 02_AGENT/agnnes_assessment_parsed.json + agent_assessment_01.json + agent_final_assessment.json
"""
import sys, json, time
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
import agnnes_agent

run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"
agent_dir = run_dir / "02_AGENT"

# 读取 observation
obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8"))
method = obs["tool_name"]
policy = obs.get("parameter_policy_used", {})

# 读取 probe observations
probe_obs = []
for i in (1, 2):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        probe_obs.append(json.loads(p.read_text(encoding="utf-8")))

# 构造 assessment prompt
aprompt = agnnes_agent.build_assessment_prompt(obs, [], method, policy,
                                                probe_observations=probe_obs)
with open(run_dir / "01_AGH" / "agnnes_assessment_prompt.json", "w", encoding="utf-8") as f:
    json.dump({"prompt": json.loads(aprompt)}, f, indent=2, ensure_ascii=False, default=str)
print("[OK] assessment prompt written")
print(aprompt[:2000])
print("...")

# 读取 Agnes raw assessment（AGH session 写入）
raw_path = run_dir / "01_AGH" / "agnnes_raw_assessment.json"
if not raw_path.exists():
    print(f"[STOP] {raw_path.name} not found — AGH session must write it first")
    sys.exit(1)

raw = raw_path.read_text(encoding="utf-8")
assessment = agnnes_agent.agnes_assess_from_raw(obs, [], method, policy, raw)

with open(agent_dir / "agnnes_assessment_parsed.json", "w", encoding="utf-8") as f:
    json.dump(assessment, f, indent=2, ensure_ascii=False, default=str)
with open(agent_dir / "agent_assessment_01.json", "w", encoding="utf-8") as f:
    json.dump(assessment, f, indent=2, ensure_ascii=False, default=str)
with open(agent_dir / "agent_final_assessment.json", "w", encoding="utf-8") as f:
    json.dump(assessment, f, indent=2, ensure_ascii=False, default=str)

if "_error" in assessment:
    print(f"[ERROR] assessment guardrail: {assessment['_error']}")
    sys.exit(2)

print(f"[ASSESSMENT] decision={assessment['decision']} confidence={assessment.get('confidence')}")
print(f"  reason: {assessment.get('reason')}")
if assessment.get("_guardrail_applied"):
    print(f"  [GUARDRAIL] {assessment['_guardrail_applied']}")
