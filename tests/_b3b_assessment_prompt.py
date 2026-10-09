"""B3B: generate Agnes assessment prompt for attempt 01 (round after registration)."""
import sys, json
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
import agnnes_agent

run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
agent_dir = run_dir / "02_AGENT"
attempt_dir = run_dir / "attempts" / "attempt_01"

obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8-sig"))
probes_run = []
probe_obs = []
for i in (1, 2):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs_p = json.loads(p.read_text(encoding="utf-8-sig"))
        probe_obs.append(obs_p)
        probes_run.append(obs_p.get("_probe_request", {}).get("probe_name") or obs_p.get("probe_name"))

prompt = agnnes_agent.build_assessment_prompt(
    observation=obs,
    prior_attempts=[],
    current_method=obs.get("tool_name", ""),
    current_policy=obs.get("parameter_policy_used", {}),
    probe_observations=probe_obs)

out = run_dir / "01_AGH" / "agnnes_assessment_prompt.json"
out.write_text(json.dumps({"prompt": json.loads(prompt), "meta": {"attempts": ["attempt_01"]}},
                          indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print("--- ASSESSMENT PROMPT JSON (for subagent_fork) ---")
print(prompt)
