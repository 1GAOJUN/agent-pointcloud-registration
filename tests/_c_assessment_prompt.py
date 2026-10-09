"""Phase C: generate Agnes assessment prompt for a given attempt number.

Usage:
  python tests/_c_assessment_prompt.py --run-dir <current_run_dir> --attempt <attempt_no>
"""
import argparse, sys, json
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
import agnnes_agent

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", required=True, type=Path)
parser.add_argument("--attempt", dest="attempt_no", type=int, default=1)
args = parser.parse_args()
run_dir = args.run_dir.resolve()
if not run_dir.is_dir():
    parser.error(f"run directory does not exist: {run_dir}")
agent_dir = run_dir / "02_AGENT"

attempt_no = args.attempt_no
obs = json.loads((agent_dir / f"observation_{attempt_no:02d}.json").read_text(encoding="utf-8-sig"))

probes_run = []
probe_obs = []
for i in range(1, 3):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs_p = json.loads(p.read_text(encoding="utf-8-sig"))
        probe_obs.append(obs_p)
        probes_run.append(obs_p.get("_probe_request", {}).get("probe_name") or obs_p.get("probe_name"))

prior_attempts = []
attempt_dirs = sorted((run_dir / "attempts").glob("attempt_*"))
for ad in attempt_dirs:
    summ = ad / "attempt_summary.json"
    if summ.exists() and ad.name != f"attempt_{attempt_no:02d}":
        prior_attempts.append(json.loads(summ.read_text(encoding="utf-8")))

prompt = agnnes_agent.build_assessment_prompt(
    observation=obs,
    prior_attempts=prior_attempts,
    current_method=obs.get("tool_name", ""),
    current_policy=obs.get("parameter_policy_used", {}),
    probe_observations=probe_obs)

out = run_dir / "01_AGH" / f"agnnes_assessment_prompt_attempt_{attempt_no:02d}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"prompt": json.loads(prompt), "meta": {"run_id": run_dir.name, "attempt": attempt_no,
                                                                   "prior_attempts_count": len(prior_attempts)}},
                          indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"[OK] assessment prompt attempt={attempt_no} saved to {out.name}")
print("--- ASSESSMENT PROMPT JSON (for subagent_fork) ---")
print(prompt)
