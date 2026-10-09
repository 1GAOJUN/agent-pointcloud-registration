"""B3B: Independent GT Evaluator — runs ONLY after Agent stops (ACCEPT/ABORT).

Reads est transform from observation_01.json, GT from case dir,
computes rotation_error_deg / translation_error / success.
Saves evaluator_result.json to 05_VALIDATION/ + run dir root + attempts/attempt_01/.
"""
import json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))
from agent_evaluator import evaluate_agent_result, save_evaluator_result

case = ROOT / "outputs" / "ICP" / "L2" / "L2" / "seed_202"
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
agent_dir = run_dir / "02_AGENT"
val_dir = run_dir / "05_VALIDATION"
attempt_dir = run_dir / "attempts" / "attempt_01"

# Confirm agent stopped with terminal decision before touching GT
final = json.loads((agent_dir / "agent_final_assessment.json").read_text(encoding="utf-8-sig"))
assert final.get("decision") in ("ACCEPT", "ABORT"), f"Agent not stopped: {final.get('decision')}"
print(f"[gate] agent final decision = {final.get('decision')} — proceeding to GT evaluation")

obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8-sig"))
T_est = np.asarray(obs["transform"], dtype=np.float64)

res = evaluate_agent_result(T_est, str(case / "gt_transform.npy"))
res["final_agent_decision"] = final.get("decision")
res["estimated_transform"] = T_est.tolist()

for p in (val_dir / "evaluator_result.json", attempt_dir / "evaluator_result.json",
          run_dir / "evaluator_result.json"):
    save_evaluator_result(res, str(p))

print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
