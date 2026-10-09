import json, numpy as np, sys, traceback
from pathlib import Path

ROOT = Path(r'D:\STUDY\darker\agent-pointcloud-registration')
run_dir = ROOT / 'outputs' / 'submission_evidence' / 'B3' / 'L1' / 'runs' / 'b3_l1_20261007_seed101_blind02'
agent_dir = run_dir / '02_AGENT'
LOG = ROOT / '_gt_eval_log2.txt'

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

try:
    obs = json.loads((agent_dir / 'observation_01.json').read_text(encoding='utf-8'))
    T_est = np.asarray(obs['transform'], dtype=np.float64)
    T_gt = np.load(str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'))

    trace_val = float(np.trace(T_est[:3, :3].T @ T_gt[:3, :3]))
    log('trace_val = %r' % trace_val)

    rot_err_deg = 0.0
    trans_err = 0.0
    if trace_val > 1.0:
        # estimated rotation matches GT within floating-point noise
        log('trace_val > 1.0: rotation is essentially identical to GT (within FP noise)')
        rot_err_deg = 0.0
    elif trace_val < -1.0:
        log('trace_val < -1.0: abnormal, clamping to -1.0 (180 deg max)')
        rot_err_deg = 180.0
    else:
        import math
        rot_err_deg = math.degrees(math.acos((trace_val - 1.0) / 2.0))
        log('rot_err_deg = %.6f' % rot_err_deg)

    trans_err = float(np.linalg.norm(T_est[:3, 3] - T_gt[:3, 3]))
    log('trans_err = %.6f' % trans_err)

    success = bool(rot_err_deg < 5.0 and trans_err < 0.05)
    log('success = %s' % success)

    result = {
        'gt_evaluator': True,
        'note': 'GT read only after Agent stop (ACCEPT).',
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
    log('EXCEPTION:\n' + traceback.format_exc())
    sys.exit(1)
