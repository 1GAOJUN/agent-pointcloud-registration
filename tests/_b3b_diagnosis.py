"""B3B Basic Diagnosis + input summary + decision_input_snapshot for case_unknown_B.

Case data: outputs/ICP/L2/L2/seed_202/ (Python-only path, withheld from Agnes).
Run dir: outputs/submission_evidence/B3/L2/runs/b3_l2_20261007_seed202_blind01/
"""
import sys, json, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose

case = ROOT / "outputs" / "ICP" / "L2" / "L2" / "seed_202"
source_ply = str(case / "source.ply")
target_ply = str(case / "target.ply")
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L2" / "runs" / "b3_l2_20261007_seed202_blind01"
agent_dir = run_dir / "02_AGENT"
agent_dir.mkdir(parents=True, exist_ok=True)

assert "seed_202" in source_ply and "source.ply" in source_ply and "seed_202" in target_ply and "target.ply" in target_ply, "case data must be seed_202 L2"
assert (case / "gt_transform.npy").exists(), "GT must exist for evaluator (not read now)"

diagnosis = diagnose(source_ply, target_ply)

with open(agent_dir / "diagnosis.json", "w", encoding="utf-8") as f:
    json.dump(diagnosis, f, indent=2, ensure_ascii=False, default=str)

input_summary = {
    "case_id": "case_unknown_B",
    "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
    "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
    "source_point_count": diagnosis["source_point_count"],
    "target_point_count": diagnosis["target_point_count"],
    "initial_transform_available": diagnosis["initial_transform_available"],
    "note": "Agent decision stage does not receive full paths, L1/L2/L3/L4 level labels, seed, or historical results.",
}
with open(agent_dir / "input_summary.json", "w", encoding="utf-8") as f:
    json.dump(input_summary, f, indent=2, ensure_ascii=False, default=str)

# decision_input_snapshot.json — everything Agnes will see before its first decision call.
# This is the audit artifact for the input leakage check.
snapshot = {
    "snapshot_purpose": "Pre-Agnes-decision input audit. Captured before first real Agnes decision call.",
    "case_label": "case_unknown_B",
    "inputs_visible_to_agnnes": {
        "input_summary": input_summary,
        "diagnosis": diagnosis,
    },
    "inputs_NOT_visible_to_agnnes": [
        "disk paths (source.ply / target.ply / gt_transform.npy)",
        "level label (L2)",
        "seed (202)",
        "rotation/translation magnitude description",
        "historical B0 result",
        "B3A result",
        "GT transform values",
    ],
}
with open(agent_dir / "decision_input_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps({"diagnosis": diagnosis, "input_summary": input_summary}, indent=2, ensure_ascii=False, default=str))
