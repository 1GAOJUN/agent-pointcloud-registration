"""B3A Basic Diagnosis + 输入摘要 生成脚本。

从 data/L1/seed_101/ 读取 source.ply / target.ply，
执行 agent_diagnose.diagnose()，写入 run 目录 diagnosis.json + input_summary.json。
不含 GT、不含路径（Agnes 只看到匿名 source_cloud/target_cloud 标签）。
"""
import sys, json, time
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose

case = ROOT / "data" / "L1" / "seed_101"
source_ply = str(case / "source.ply")
target_ply = str(case / "target.ply")
run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"

diagnosis = diagnose(source_ply, target_ply)

# 写入 02_AGENT/
agent_dir = run_dir / "02_AGENT"
agent_dir.mkdir(parents=True, exist_ok=True)
with open(agent_dir / "diagnosis.json", "w", encoding="utf-8") as f:
    json.dump(diagnosis, f, indent=2, ensure_ascii=False, default=str)

# 输入摘要：匿名，不含磁盘路径/场景标签
input_summary = {
    "case_id": "case_unknown_A",
    "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
    "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
    "source_point_count": diagnosis["source_point_count"],
    "target_point_count": diagnosis["target_point_count"],
    "initial_transform_available": diagnosis["initial_transform_available"],
    "note": "Agent 决策阶段不接收完整路径或 L1/L2/L3/L4 场景标签。",
}
with open(agent_dir / "input_summary.json", "w", encoding="utf-8") as f:
    json.dump(input_summary, f, indent=2, ensure_ascii=False, default=str)

print(json.dumps({"diagnosis": diagnosis, "input_summary": input_summary}, indent=2, ensure_ascii=False, default=str))
