"""B3A Pre-flight 最小环境检查。

检查项：
1. 当前实际 Python executable
2. import open3d 是否成功
3. Open3D 版本
4. 读取一个现有 PLY 是否成功
5. src/agent_diagnose.py 最小 diagnosis smoke 是否成功

成功 → 打印 PASS_JSON
失败 → 打印 FAIL_JSON，exit 1
"""
import sys, json, time, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

results = {}
passed = True

# 1. Python executable
results["python_executable"] = sys.executable

# 2. import open3d
try:
    import open3d as o3d
    results["open3d_import"] = "OK"
except Exception as e:
    results["open3d_import"] = f"FAIL: {e}"
    passed = False
    print(json.dumps({"status": "FAIL", "results": results}, indent=2, ensure_ascii=False))
    sys.exit(1)

# 3. Open3D version
results["open3d_version"] = o3d.__version__

# 4. PLY read
try:
    ply_path = str(ROOT / "data" / "L1" / "seed_101" / "source.ply")
    pc = o3d.io.read_point_cloud(ply_path)
    if pc is None:
        raise RuntimeError("read_point_cloud returned None")
    results["ply_read"] = f"OK: {len(pc.points)} points from {os.path.basename(ply_path)}"
except Exception as e:
    results["ply_read"] = f"FAIL: {e}"
    passed = False
    print(json.dumps({"status": "FAIL", "results": results}, indent=2, ensure_ascii=False))
    sys.exit(1)

# 5. agent_diagnose smoke
try:
    from agent_diagnose import diagnose
    diag = diagnose(str(ROOT / "data" / "L1" / "seed_101" / "source.ply"),
                    str(ROOT / "data" / "L1" / "seed_101" / "target.ply"))
    required_keys = {"source_point_count", "target_point_count", "base_scale",
                     "centroid_distance", "initial_transform_available"}
    missing = required_keys - set(diag.keys())
    if missing:
        raise RuntimeError(f"diagnosis missing keys: {missing}")
    results["diagnose_smoke"] = f"OK: base_scale={diag['base_scale']:.6f}, src={diag['source_point_count']}pts"
except Exception as e:
    results["diagnose_smoke"] = f"FAIL: {e}"
    passed = False

status = "PASS" if passed else "FAIL"
out = {"status": status, "results": results, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
print(json.dumps(out, indent=2, ensure_ascii=False))
sys.exit(0 if passed else 1)
