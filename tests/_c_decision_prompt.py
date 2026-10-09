"""Phase C: Generate Agnes decision prompt for round N.

Usage:
  python tests/_c_decision_prompt.py --run-dir <current_run_dir> --round <round_no>

Output:
  01_AGH/agnnes_decision_prompt_NN.json
  Prints prompt JSON to stdout (for subagent_fork)
"""
import argparse, sys, json
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_tools import TOOL_REGISTRY
import agnnes_agent

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", required=True, type=Path)
parser.add_argument("--round", dest="round_no", type=int, default=1)
args = parser.parse_args()
run_dir = args.run_dir.resolve()
if not run_dir.is_dir():
    parser.error(f"run directory does not exist: {run_dir}")
agent_dir = run_dir / "02_AGENT"

round_no = args.round_no

diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8"))

# Load prior probe observations (files with index < round_no)
probes_run: list = []
probe_obs: list = []
for i in range(1, round_no):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs = json.loads(p.read_text(encoding="utf-8"))
        probe_obs.append(obs)
        probes_run.append(obs.get("_probe_request", {}).get("probe_name") or obs.get("probe_name"))

# Load prior attempts (RETRY guardrail: feed compact GT-free observation back)
prior_attempts: list = []
attempt_dirs = sorted((run_dir / "attempts").glob("attempt_*")) if (run_dir / "attempts").exists() else []
for ad in attempt_dirs:
    summ = ad / "attempt_summary.json"
    if summ.exists():
        prior_attempts.append(json.loads(summ.read_text(encoding="utf-8")))

prompt = agnnes_agent.build_decision_prompt(
    diagnosis, TOOL_REGISTRY, prior_attempts,
    probes_already_run=probes_run, probe_observations=probe_obs)

out = run_dir / "01_AGH" / f"agnnes_decision_prompt_{round_no:02d}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"prompt": json.loads(prompt),
                           "meta": {"run_id": run_dir.name, "round": round_no, "probes_already_run": probes_run,
                                     "prior_attempts_count": len(prior_attempts)}},
                          indent=2, ensure_ascii=False, default=str), encoding="utf-8")

print(f"[OK] prompt round={round_no} probes_already_run={probes_run} prior_attempts={len(prior_attempts)}")
print("--- PROMPT JSON (for subagent_fork) ---")
print(prompt)
