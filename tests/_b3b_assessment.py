"""B3B: parse + guardrail Agnes assessment, save to agent/attempt dirs."""
import json, sys
from pathlib import Path
ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
import agnnes_agent

run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
agent_dir = run_dir / "02_AGENT"
attempt_dir = run_dir / "attempts" / "attempt_01"

raw_path = run_dir / "01_AGH" / "agnnes_raw_assessment.json"
raw = raw_path.read_text(encoding="utf-8-sig")

obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8-sig"))
res = agnnes_agent.agnes_assess_from_raw(obs, [], obs.get("tool_name", ""), obs.get("parameter_policy_used", {}), raw)

for f in ("agnnes_assessment_parsed.json", "agent_assessment_01.json", "agent_final_assessment.json"):
    txt = json.dumps(res, indent=2, ensure_ascii=False, default=str)
    (agent_dir / f).write_text(txt, encoding="utf-8")
    (attempt_dir / f).write_text(txt, encoding="utf-8")

# also save the tool_call/params into attempt dir for completeness
import shutil
for src, dst in (
    (run_dir / "03_TOOL_CHAIN" / "tool_call_01.json", attempt_dir / "tool_call_01.json"),
    (run_dir / "04_CONFIG" / "parameters.json", attempt_dir / "parameters.json"),
):
    if src.exists():
        shutil.copyfile(str(src), str(dst))

attempt_summary = {
    "attempt_no": 1,
    "final_agent_decision": res.get("decision"),
    "method": obs.get("tool_name"),
    "parameter_policy": obs.get("parameter_policy_used"),
    "fitness": obs.get("fitness"),
    "rmse": obs.get("rmse"),
    "retried": False,
}
(attempt_dir / "attempt_summary.json").write_text(json.dumps(attempt_summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
