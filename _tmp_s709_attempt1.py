"""Run the RANSAC step in isolation, save result to cache."""
import sys, time, json
import numpy as np
sys.path.insert(0, 'D:/STUDY/darker/agent-pointcloud-registration/src')
import open3d as o3d
from agent_tools import _load, _ensure_normals

SRC = 'D:/STUDY/darker/agent-pointcloud-registration/data/formal_blind/case_unknown_C_20261008_s709/agent_input/source_cloud.ply'
TGT = 'D:/STUDY/darker/agent-pointcloud-registration/data/formal_blind/case_unknown_C_20261008_s709/agent_input/target_cloud.ply'
BASE_SCALE = 0.03389227529867417
GLOBAL_CORR_SCALE = 4.0
ICP_CORR_SCALE = 2.0

np.random.seed(42)
t0 = time.perf_counter()
print("Loading clouds...", flush=True)
source = _load(SRC)
target = _load(TGT)
source, _ = source.remove_statistical_outlier(nb_neighbors=30, std_ratio=1.0)
target, _ = target.remove_statistical_outlier(nb_neighbors=30, std_ratio=1.0)
normal_radius = max(1e-3, BASE_SCALE * 0.5)
source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=30))
target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=normal_radius, max_nn=30))

import open3d.pipelines.registration as reg
n_key = min(500, len(source.points))
step = max(1, len(source.points) // n_key)
src_idx = list(range(0, len(source.points), step))[:n_key]
n_key_t = min(500, len(target.points))
step_t = max(1, len(target.points) // n_key_t)
tgt_idx = list(range(0, len(target.points), step_t))[:n_key_t]

fpfh_radius = max(BASE_SCALE, 0.2)
search = o3d.geometry.KDTreeSearchParamHybrid(radius=fpfh_radius, max_nn=30)
print("Computing FPFH features...", flush=True)
src_f = reg.compute_fpfh_feature(source, search, src_idx)
tgt_f = reg.compute_fpfh_feature(target, search, tgt_idx)

ransac_corr = max(1e-3, float(BASE_SCALE) * float(GLOBAL_CORR_SCALE))
print(f"RANSAC corr threshold: {ransac_corr}", flush=True)
t_ransac = time.perf_counter()
print("Running RANSAC (this is the slow step)...", flush=True)
ransac = reg.registration_ransac_based_on_feature_matching(
    source, target, src_f, tgt_f,
    mutual_filter=True, max_correspondence_distance=ransac_corr,
)
t_ransac_elapsed = time.perf_counter() - t_ransac
ransac_T = np.asarray(ransac.transformation, dtype=np.float64)
print(f"RANSAC done in {t_ransac_elapsed:.1f}s: fitness={ransac.fitness:.4f} rmse={ransac.inlier_rmse:.4f}", flush=True)

icp_corr = max(1e-4, float(BASE_SCALE) * float(ICP_CORR_SCALE))
print(f"ICP corr threshold: {icp_corr}", flush=True)
t_icp = time.perf_counter()
icp = reg.registration_icp(
    source, target, icp_corr,
    ransac_T,
    estimation_method=reg.TransformationEstimationPointToPlane(),
    criteria=reg.ICPConvergenceCriteria(max_iteration=100, relative_fitness=1e-6, relative_rmse=1e-6),
)
t_icp_elapsed = time.perf_counter() - t_icp
print(f"ICP done in {t_icp_elapsed:.1f}s: fitness={icp.fitness:.4f} rmse={icp.inlier_rmse:.4f}", flush=True)

T = np.asarray(icp.transformation, dtype=np.float64)
out = {
  "fitness": float(icp.fitness),
  "rmse": float(icp.inlier_rmse),
  "ransac_fitness": float(ransac.fitness),
  "ransac_rmse": float(ransac.inlier_rmse),
  "elapsed_s": round(float(t_ransac_elapsed + t_icp_elapsed), 3),
  "ransac_elapsed_s": round(float(t_ransac_elapsed), 3),
  "icp_elapsed_s": round(float(t_icp_elapsed), 3),
  "ransac_max_correspondence_distance": float(ransac_corr),
  "icp_max_correspondence_distance": float(icp_corr),
  "transform": T.tolist(),
}
with open('D:/STUDY/darker/agent-pointcloud-registration/_tmp_s709_attempt1.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("Saved _tmp_s709_attempt1.json")
print(json.dumps({k: v for k, v in out.items() if k != 'transform'}, indent=2, ensure_ascii=False))
