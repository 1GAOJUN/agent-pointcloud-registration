"""Print the next Agnes decision prompt to stdout (for AGH session handoff).

Usage (from project root):
  python tests/_b2b_print_next_prompt.py [N]
  N = next decision round number (1, 2, or 3).
  Round 1: no probes yet. Round 2: after probe observation 01. Round 3: after 02.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY
import agnnes_agent

round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1

case = ROOT / "outputs" / "ICP" / "L1" / "L1" / "seed_101"
diagnosis = diagnose(str(case / "source.ply"), str(case / "target.ply"))

out_dir = ROOT / "outputs" / "development_tests" / "B2B_ACTIVE_PROBE_SMOKE"
probes_run: list[str] = []
probe_obs: list[dict] = []
# Probe observations are numbered 1..N in execution order; all observations
# with index < round_no are already executed before round_no's Agnes call.
for i in range(1, round_no):
    p = out_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs = json.loads(p.read_text(encoding="utf-8"))
        probe_obs.append(obs)
        probes_run.append(obs.get("_probe_request", {}).get("probe_name") or obs.get("probe_name"))

prompt = agnnes_agent.build_decision_prompt(
    diagnosis, TOOL_REGISTRY, [],
    probes_already_run=probes_run, probe_observations=probe_obs)
out = out_dir / f"agnnes_decision_prompt_{round_no:02d}.json"
out.write_text(json.dumps({"prompt": json.loads(prompt),
                          "meta": {"round": round_no, "probes_already_run": probes_run}},
                         indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"round={round_no} probes_already_run={probes_run} -> {out.name}")
