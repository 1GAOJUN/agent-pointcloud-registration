"""B2B development: cost profile of formal LOCAL_ICP + probe candidate config.
Writes JSON summary to outputs/development_tests/B2B_ACTIVE_PROBE_SMOKE/_cost_profile.json
"""
import json, sys, time
from pathlib import Path
import numpy as np
import open3d as o3d

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_diagnose import diagnose
from agent_tools import _load, _ensure_normals

case = ROOT / "outputs" / "ICP" / "L2" / "L2" / "seed_202"
src_ply, tgt_ply = str(case / "source.ply"), str(case / "target.ply")

t0 = time.perf_counter()
diag = diagnose(src_ply, tgt_ply)
t_diag = time.perf_counter() - t0

base_scale = float(diag["base_scale"])
icp_scale = 2.0
max_corr = max(1e-4, base_scale * icp_scale)

source = _load(src_ply)
target = _load(tgt_ply)
_ensure_normals(source, search_radius=max_corr * 1.5)
_ensure_normals(target, search_radius=max_corr * 1.5)

est = o3d.pipelines.registration.TransformationEstimationPointToPlane()

def run_icp(max_iteration):
    crit = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-6, relative_rmse=1e-8, max_iteration=max_iteration)
    t0 = time.perf_counter()
    res = o3d.pipelines.registration.registration_icp(
        source, target, max_corr, np.eye(4),
        estimation_method=est, criteria=crit)
    wall = time.perf_counter() - t0
    return res, wall

res_full, wall_full = run_icp(100)
res_probe, wall_probe = run_icp(5)

out = {
    "case": "L2/L2/seed_202 (development cost profiling only)",
    "diagnosis_elapsed_s": round(t_diag, 3),
    "base_scale": base_scale,
    "icp_scale": icp_scale,
    "max_correspondence_distance": max_corr,
    "formal_local_icp": {
        "iterations": 100,
        "fitness": float(res_full.fitness),
        "rmse": float(res_full.inlier_rmse),
        "elapsed_s": round(wall_full, 3),
        "transform": np.asarray(res_full.transformation).tolist(),
    },
    "probe_local_icp": {
        "iterations": 5,
        "fitness": float(res_probe.fitness),
        "rmse": float(res_probe.inlier_rmse),
        "elapsed_s": round(wall_probe, 3),
        "transform_delta_magnitude": float(np.linalg.norm(
            np.asarray(res_probe.transformation) - np.eye(4))),
    },
}
out_dir = ROOT / "outputs" / "development_tests" / "B2B_ACTIVE_PROBE_SMOKE"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "_cost_profile.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
