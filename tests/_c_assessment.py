"""Phase C: parse + guardrail Agnes assessment for attempt N, save evidence, write attempt summary.

Usage:
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_c_assessment.py <attempt_no>

Reads 01_AGH/agnnes_raw_assessment_attempt_NN.json (written by the AGH session before this call).
GT is NOT read. Exits 0 if decision is terminal (ACCEPT/ABORT); exits 10 if RETRY.
"""
import json, sys, shutil
from pathlib import Path
ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
import agnnes_agent

run_dir = ROOT / "outputs" / "submission_evidence" / "C" / "runs" / "c_unknown_20261008_s707_blind01"
agent_dir = run_dir / "02_AGENT"
attempt_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
attempt_dir = run_dir / "attempts" / f"attempt_{attempt_no:02d}"
attempt_dir.mkdir(parents=True, exist_ok=True)

raw_path = run_dir / "01_AGH" / f"agnnes_raw_assessment_attempt_{attempt_no:02d}.json"
raw = raw_path.read_text(encoding="utf-8-sig")
try:
    _envelope = json.loads(raw)
    if isinstance(_envelope, dict) and "text_payload" in _envelope and str(_envelope.get("invocation", "")).startswith("agh"):
        raw = _envelope["text_payload"]
except (json.JSONDecodeError, TypeError):
    pass

obs = json.loads((agent_dir / f"observation_{attempt_no:02d}.json").read_text(encoding="utf-8-sig"))

# Prior attempts = all attempts with a summary except the current one
prior_attempts = []
for ad in sorted((run_dir / "attempts").glob("attempt_*")):
    summ = ad / "attempt_summary.json"
    if summ.exists() and ad.name != f"attempt_{attempt_no:02d}":
        prior_attempts.append(json.loads(summ.read_text(encoding="utf-8")))

res = agnnes_agent.agnes_assess_from_raw(
    obs, prior_attempts, obs.get("tool_name", ""), obs.get("parameter_policy_used", {}), raw)

if "_error" in res:
    print(f"[ERROR] assessment guardrail: {res['_error']}")
    sys.exit(2)

txt = json.dumps(res, indent=2, ensure_ascii=False, default=str)
(agent_dir / f"agnnes_assessment_parsed_attempt_{attempt_no:02d}.json").write_text(txt, encoding="utf-8")
(agent_dir / f"agent_assessment_{attempt_no:02d}.json").write_text(txt, encoding="utf-8")
(attempt_dir / f"agent_assessment_{attempt_no:02d}.json").write_text(txt, encoding="utf-8")

# If terminal decision, also mirror as agent_final_assessment.json
if res.get("decision") in ("ACCEPT", "ABORT"):
    (agent_dir / "agent_final_assessment.json").write_text(txt, encoding="utf-8")
    (attempt_dir / "agent_final_assessment.json").write_text(txt, encoding="utf-8")

# Copy tool chain evidence into attempt dir
for src, dst in (
    (run_dir / "03_TOOL_CHAIN" / f"tool_call_{attempt_no:02d}.json", attempt_dir / f"tool_call_{attempt_no:02d}.json"),
    (run_dir / "04_CONFIG" / f"parameters_attempt_{attempt_no:02d}.json", attempt_dir / f"parameters_attempt_{attempt_no:02d}.json"),
):
    if src.exists():
        shutil.copyfile(str(src), str(dst))

attempt_summary = {
    "attempt_no": attempt_no,
    "final_agent_decision": res.get("decision"),
    "method": obs.get("tool_name"),
    "parameter_policy": obs.get("parameter_policy_used"),
    "fitness": obs.get("fitness"),
    "rmse": obs.get("rmse"),
    "assessment_reason": res.get("reason"),
    "next_method": res.get("next_method"),
    "next_parameter_policy": res.get("next_parameter_policy"),
    "confidence": res.get("confidence"),
}
(attempt_dir / "attempt_summary.json").write_text(
    json.dumps(attempt_summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
if res.get("decision") == "RETRY":
    print("[RETRY] next round required")
    sys.exit(10)
print("[TERMINAL]", res.get("decision"))
