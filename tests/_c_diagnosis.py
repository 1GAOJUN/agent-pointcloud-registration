"""Phase C (case_unknown_C) Basic Diagnosis + input summary + decision_input_snapshot.

Case data: data/formal_blind/case_unknown_C_20261008_s707/agent_input/ (Python-only,
anonymous input paths; withheld from Agnes). Evaluator-only GT stays unread until stage 8.
Run dir: outputs/submission_evidence/C/runs/c_unknown_20261008_s707_blind01/
"""
import sys, json
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose

case = ROOT / "data" / "formal_blind" / "case_unknown_C_20261008_s707"
source_ply = str(case / "agent_input" / "source_cloud.ply")
target_ply = str(case / "agent_input" / "target_cloud.ply")
run_dir = ROOT / "outputs" / "submission_evidence" / "C" / "runs" / "c_unknown_20261008_s707_blind01"
agent_dir = run_dir / "02_AGENT"
agent_dir.mkdir(parents=True, exist_ok=True)

assert (case / "evaluator_only" / "gt_transform.npy").exists(), "GT must exist for evaluator (not read now)"

diagnosis = diagnose(source_ply, target_ply)

with open(agent_dir / "diagnosis.json", "w", encoding="utf-8") as f:
    json.dump(diagnosis, f, indent=2, ensure_ascii=False, default=str)

input_summary = {
    "case_id": "case_unknown_C",
    "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
    "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
    "source_point_count": diagnosis["source_point_count"],
    "target_point_count": diagnosis["target_point_count"],
    "initial_transform_available": diagnosis["initial_transform_available"],
    "note": "Agent decision stage does not receive full paths, L1/L2/L3/L4 level labels, seed, or historical results.",
}
with open(agent_dir / "input_summary.json", "w", encoding="utf-8") as f:
    json.dump(input_summary, f, indent=2, ensure_ascii=False, default=str)

# decision_input_snapshot.json — audit artifact for the input leakage check.
snapshot = {
    "snapshot_purpose": "Pre-Agnes-decision input audit. Captured before first real Agnes decision call.",
    "case_label": "case_unknown_C",
    "inputs_visible_to_agnnes": {
        "input_summary": input_summary,
        "diagnosis": diagnosis,
    },
    "inputs_NOT_visible_to_agnnes": [
        "disk paths (source_cloud.ply / target_cloud.ply / gt_transform.npy)",
        "level label",
        "seed",
        "rotation/translation magnitude description",
        "historical B0/B3A/B3B results",
        "GT transform values",
    ],
}
with open(agent_dir / "decision_input_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps({"diagnosis": diagnosis, "input_summary": input_summary}, indent=2, ensure_ascii=False, default=str))
