"""Execute CHEAP_LOCAL_ICP probe (requested by Agnes round 2) and write observation."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_diagnose import diagnose
from agent_probes import run_cheap_local_icp_probe

case = ROOT / "outputs" / "ICP" / "L1" / "L1" / "seed_101"
src, tgt = str(case / "source.ply"), str(case / "target.ply")
diagnosis = diagnose(src, tgt)
base_scale = float(diagnosis["base_scale"])

out_dir = ROOT / "outputs" / "development_tests" / "B2B_ACTIVE_PROBE_SMOKE"
prev1 = out_dir / "probe_observation_01.json"
req1 = json.loads(prev1.read_text(encoding="utf-8"))["_probe_request"] if prev1.exists() else {}

obs = run_cheap_local_icp_probe(src, tgt, base_scale=base_scale)
# Attach the Agnes request record from the round-2 raw decision (probe_reason)
raw2 = out_dir / "agnnes_raw_decision_02.json"
if raw2.exists():
    d2 = json.loads(raw2.read_text(encoding="utf-8"))
    obs["_probe_request"] = {
        "probe_name": "CHEAP_LOCAL_ICP",
        "requested_by": "agnnes_real",
        "round": 2,
        "probe_reason": d2.get("probe_reason"),
    }
(out_dir / "probe_observation_02.json").write_text(
    json.dumps(obs, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(obs, indent=2, ensure_ascii=False, default=str))
