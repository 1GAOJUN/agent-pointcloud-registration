"""B3A GT Evaluator — pure Python (no BLAS matmul to avoid DLL state issue).

Uses float index access and arithmetic only, no numpy BLAS calls.
"""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(r'D:\STUDY\darker\agent-pointcloud-registration')
run_dir = ROOT / 'outputs' / 'submission_evidence' / 'B3' / 'L1' / 'runs' / 'b3_l1_20261007_seed101_blind02'
agent_dir = run_dir / '02_AGENT'
LOG = ROOT / '_gt_eval_log_final.txt'

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

try:
    obs = json.loads((agent_dir / 'observation_01.json').read_text(encoding='utf-8'))
    T_est_list = obs['transform']  # 4x4 list
    T_gt = np.load(str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'))

    # trace(T_est[:3,:3]^T @ T_gt[:3,:3]) = Frobenius inner product of rotation parts
    # = sum_i sum_j T_est[j,i] * T_gt[j,i] for i,j in 0..2
    trace_val = 0.0
    for j in range(3):
        for i in range(3):
            trace_val += float(T_est_list[j][i]) * float(T_gt[j, i])
    log('trace_val = %r' % trace_val)

    # rotation error
    cos_val = (trace_val - 1.0) / 2.0
    cos_val = max(-1.0, min(1.0, cos_val))
    rot_err_deg = math.degrees(math.acos(cos_val))
    log('rot_err_deg = %.6f' % rot_err_deg)

    # translation error (pure Python)
    t_est = [float(T_est_list[i][3]) for i in range(3)]
    t_gt = [float(T_gt[i, 3]) for i in range(3)]
    trans_err = math.sqrt(sum((a - b) ** 2 for a, b in zip(t_est, t_gt)))
    log('trans_err = %.6f' % trans_err)

    success = bool(rot_err_deg < 5.0 and trans_err < 0.05)
    log('success = %s' % success)

    result = {
        'gt_evaluator': True,
        'note': 'GT read only after Agent stop (ACCEPT). Pure-Python computation (no BLAS matmul).',
        'rot_err_deg': rot_err_deg,
        'trans_err': trans_err,
        'success': success,
        'rot_thr_deg': 5.0,
        'trans_thr': 0.05,
        'gt_path': str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'),
    }
    (agent_dir / 'evaluator_result.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    log('evaluator_result.json written')
    print('EVAL: rot_err_deg=%.6f trans_err=%.6f success=%s' % (rot_err_deg, trans_err, success))
except Exception:
    import traceback
    log('EXCEPTION:\n' + traceback.format_exc())
    sys.exit(1)
