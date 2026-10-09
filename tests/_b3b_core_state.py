"""B3B: update B3B_CORE_STATE.json after a stage completes."""
import sys, json, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
state_path = run_dir / "00_INDEX" / "B3B_CORE_STATE.json"

stage = sys.argv[1]  # e.g. "1_DIAGNOSIS"
status = sys.argv[2] if len(sys.argv) > 2 else "COMPLETED"
evidence = sys.argv[3] if len(sys.argv) > 3 else ""

state = json.loads(state_path.read_text(encoding="utf-8-sig"))
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
state["stage"] = stage
state["stage_completed"] = True
state["stage_timestamp_utc"] = now
if stage in state.get("core_state", {}):
    state["core_state"][stage] = {"status": status, "ts": now, "evidence_files": [evidence] if evidence else []}

state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"[CORE_STATE] {stage} -> {status} @ {now}")
