import sys, json, traceback
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
sys.path.insert(0, str(ROOT / "src"))

try:
    print("step 1: import evaluate")
    from evaluate import load_transform, rotation_error_deg, translation_error, judge_success
    print("step 2: load obs")
    run_dir = ROOT / "outputs" / "submission_evidence" / "B3" / "L1" / "runs" / "b3_l1_20261007_seed101_blind02"
    agent_dir = run_dir / "02_AGENT"
    obs = json.loads((agent_dir / "observation_01.json").read_text(encoding="utf-8"))
    T_est = np.asarray(obs["transform"], dtype=np.float64)
    print(f"step 3: T_est shape={T_est.shape}")
    print(f"step 4: load gt")
    case = ROOT / "data" / "L1" / "seed_101"
    T_gt = load_transform(str(case / "gt_transform.npy"))
    print(f"step 5: T_gt shape={T_gt.shape}")
    print(f"step 6: compute errors")
    rot_err = rotation_error_deg(T_est, T_gt)
    trans_err = translation_error(T_est, T_gt)
    success = judge_success({"rot_err_deg": rot_err, "trans_err": trans_err}, 5.0, 0.05)
    print(f"step 7: rot_err={rot_err} trans_err={trans_err} success={success}")
    result = {
        "gt_evaluator": True,
        "note": "GT read only after Agent stop",
        "rot_err_deg": float(rot_err),
        "trans_err": float(trans_err),
        "success": bool(success),
        "rot_thr_deg": 5.0,
        "trans_thr": 0.05,
    }
    (agent_dir / "evaluator_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"step 8: saved")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception:
    traceback.print_exc()
    sys.exit(1)
