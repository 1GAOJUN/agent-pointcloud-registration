"""B2A evaluator: compute GT error WITHOUT numpy matmul (env BLAS is broken).

Uses pure-Python float arithmetic for R.T @ R, trace, norms.
Only reads gt_transform.npy + the stored estimate transform. Writes evaluator_result.json.
"""
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE = PROJECT_ROOT / "outputs" / "development_tests" / "B2A_REAL_AGNES_SMOKE"

# --- load estimate (from observation JSON, pure Python) ---
obs = json.loads((SMOKE / "observation_01.json").read_text(encoding="utf-8"))
T_est = obs["transform"]          # 4x4 as list of lists
assert len(T_est) == 4 and all(len(r) == 4 for r in T_est)

# --- load GT via numpy only to read the file (np.load does not matmul) ---
import numpy as np
T_gt = np.load(str(PROJECT_ROOT / "outputs" / "ICP" / "L1" / "L1" / "seed_101" / "gt_transform.npy"))
T_gt = T_gt.tolist()


def mat3(a):
    return [a[0][:3], a[1][:3], a[2][:3]]


def matmul3(A, B):
    return [
        [sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def identity3():
    return [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]


def trace3(M):
    return sum(M[i][i] for i in range(3))


def sub3(A, B):
    return [[A[i][j] - B[i][j] for j in range(3)] for i in range(3)]


def absmax3(M):
    return max(abs(v) for row in M for v in row)


def norm3(v):
    return sum(x * x for x in v) ** 0.5


R_est = mat3(T_est)
R_gt = mat3(T_gt)

# orthogonality check (R.T @ R == I) without numpy matmul
def trans3(M):
    return [[M[j][i] for j in range(3)] for i in range(3)]

I3 = identity3()
ortho_est = absmax3(sub3(matmul3(trans3(R_est), R_est), I3))
ortho_gt = absmax3(sub3(matmul3(trans3(R_gt), R_gt), I3))

# rotation error: theta = arccos((tr(R_rel) - 1)/2), R_rel = R_est^T R_gt
R_rel = matmul3(trans3(R_est), R_gt)
import math
cos_theta = max(-1.0, min(1.0, (trace3(R_rel) - 1.0) / 2.0))
rot_err_deg = math.degrees(math.acos(cos_theta))

# translation error
t_est = T_est[0][3], T_est[1][3], T_est[2][3]
t_gt = T_gt[0][3], T_gt[1][3], T_gt[2][3]
trans_err = norm3([t_est[0] - t_gt[0], t_est[1] - t_gt[1], t_est[2] - t_gt[2]])

rot_thr, trans_thr = 5.0, 0.05
success = rot_err_deg < rot_thr and trans_err < trans_thr

result = {
    "gt_evaluator": True,
    "note": "GT read only here, after Agent stopped. Computed with pure-Python math (env numpy BLAS broken).",
    "rot_err_deg": rot_err_deg,
    "trans_err": trans_err,
    "success": success,
    "rot_thr_deg": rot_thr,
    "trans_thr": trans_thr,
    "gt_path": str(PROJECT_ROOT / "outputs" / "ICP" / "L1" / "L1" / "seed_101" / "gt_transform.npy"),
    "ortho_err_est": ortho_est,
    "ortho_err_gt": ortho_gt,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
}

out = SMOKE / "evaluator_result.json"
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print("gt_success =", success)
print("rot_err_deg =", round(rot_err_deg, 6))
print("trans_err =", round(trans_err, 6))
print("ortho_err_est =", ortho_est, "ortho_err_gt =", ortho_gt)
print("saved ->", out)
