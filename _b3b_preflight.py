import sys, json, os, time
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

out = {}
out["sys_executable"] = sys.executable
out["python_version"] = ".".join(str(v) for v in sys.version_info[:3])
try:
    out["python_full_version"] = sys.version
except Exception as e:
    out["python_full_version"] = str(e)
try:
    import open3d
    out["open3d_import"] = "OK"
    out["open3d_version"] = getattr(open3d, "__version__", None)
except Exception as e:
    out["open3d_import"] = "FAIL"
    out["open3d_version"] = None
    out["open3d_error"] = repr(e)

# try numpy
try:
    import numpy
    out["numpy_version"] = getattr(numpy, "__version__", None)
except Exception as e:
    out["numpy_version"] = None
    out["numpy_error"] = repr(e)

# try matplotlib
try:
    import matplotlib
    out["matplotlib_version"] = getattr(matplotlib, "__version__", None)
except Exception as e:
    out["matplotlib_version"] = None
    out["matplotlib_error"] = repr(e)

# read a known existing PLY to confirm Open3D I/O works
ply_path = r"D:\STUDY\darker\agent-pointcloud-registration\outputs\ICP\L2\L2\seed_202\source.ply"
if os.path.exists(ply_path) and out.get("open3d_import") == "OK":
    import open3d as o3d
    t0 = time.perf_counter()
    pcd = o3d.io.read_point_cloud(ply_path)
    out["ply_read_ok"] = True
    out["ply_path"] = ply_path
    out["ply_point_count"] = len(pcd.points)
    out["ply_read_time_s"] = round(time.perf_counter() - t0, 4)
else:
    out["ply_read_ok"] = False
    out["ply_path"] = ply_path

# minimal agent diagnosis smoke: import the module and call diagnose with a tiny pointcloud
try:
    sys.path.insert(0, r"D:\STUDY\darker\agent-pointcloud-registration")
    from src.agent_diagnose import diagnose
    diag = diagnose(ply_path, ply_path)  # source and target same file as smoke only
    out["diagnosis_smoke_ok"] = True
    out["diagnosis_smoke_keys"] = sorted(diag.keys()) if isinstance(diag, dict) else type(diag).__name__
except Exception as e:
    out["diagnosis_smoke_ok"] = False
    out["diagnosis_smoke_error"] = repr(e)

print(json.dumps(out, indent=2, default=str))
