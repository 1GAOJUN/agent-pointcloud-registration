"""Phase C: parse Agnes raw decision for round N, run guardrails, execute probe if requested.

Usage:
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_c_execute_probe.py <round_no>

Reads 01_AGH/agnnes_raw_decision_NN.json (written by the AGH session before this call).
The raw file may be either (a) the plain JSON decision object, or (b) a capture envelope
{model, invocation, text_payload, ...} produced by _c_agnnes_cli.py. GT is NOT read.
"""
import sys, json, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_probes import PROBE_DISPATCH, MAX_PROBES_PER_RUN
import agnnes_agent

case = ROOT / "data" / "formal_blind" / "case_unknown_C_20261008_s707"
source_ply = str(case / "agent_input" / "source_cloud.ply")
target_ply = str(case / "agent_input" / "target_cloud.ply")
run_dir = ROOT / "outputs" / "submission_evidence" / "C" / "runs" / "c_unknown_20261008_s707_blind01"
agent_dir = run_dir / "02_AGENT"

round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
raw_path = run_dir / "01_AGH" / f"agnnes_raw_decision_{round_no:02d}.json"
if not raw_path.exists():
    print(f"[ERROR] raw decision not found: {raw_path}")
    sys.exit(1)
raw = raw_path.read_text(encoding="utf-8-sig")
# Unwrap capture envelope (agh_headless_cli) if present: use text_payload as the raw JSON text.
try:
    _envelope = json.loads(raw)
    if isinstance(_envelope, dict) and "text_payload" in _envelope and _envelope.get("invocation", "").startswith("agh"):
        raw = _envelope["text_payload"]
except (json.JSONDecodeError, TypeError):
    pass

probes_run: list = []
probe_obs: list = []
for i in range(1, round_no):
    p = agent_dir / f"probe_observation_{i:02d}.json"
    if p.exists():
        obs = json.loads(p.read_text(encoding="utf-8-sig"))
        probe_obs.append(obs)
        probes_run.append(obs.get("_probe_request", {}).get("probe_name") or obs.get("probe_name"))

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
    print(f"[FINAL] method={decision['selected_method']} policy={decision.get('parameter_policy')}")
    sys.exit(0)

probe_name = decision["requested_probe"]
if probe_name not in PROBE_DISPATCH:
    print(f"[ERROR] invalid probe '{probe_name}'"); sys.exit(3)
if probe_name in probes_run:
    print(f"[ERROR] duplicate probe '{probe_name}' blocked"); sys.exit(3)
if len(probes_run) >= MAX_PROBES_PER_RUN:
    print(f"[ERROR] quota ({MAX_PROBES_PER_RUN}) exhausted; Agnes must select formal method next round")
    sys.exit(4)

diagnosis = json.loads((agent_dir / "diagnosis.json").read_text(encoding="utf-8-sig"))
base_scale = float(diagnosis.get("base_scale", 0.1))

from agent_probes import run_pca_orientation_probe, run_cheap_local_icp_probe
t0 = time.time()
if probe_name == "PCA_ORIENTATION":
    obs = run_pca_orientation_probe(source_ply, target_ply)
else:
    obs = run_cheap_local_icp_probe(source_ply, target_ply, base_scale=base_scale)
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
