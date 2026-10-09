import json, numpy as np, sys, os, traceback
from pathlib import Path

ROOT = Path(r'D:\STUDY\darker\agent-pointcloud-registration')
run_dir = ROOT / 'outputs' / 'submission_evidence' / 'B3' / 'L1' / 'runs' / 'b3_l1_20261007_seed101_blind02'
agent_dir = run_dir / '02_AGENT'
LOG = ROOT / '_gt_eval_log.txt'

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

try:
    obs = json.loads((agent_dir / 'observation_01.json').read_text(encoding='utf-8'))
    log('step1: obs loaded')
    T_est = np.asarray(obs['transform'], dtype=np.float64)
    log('step2: T_est shape=%s' % str(T_est.shape))
    T_gt = np.load(str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'))
    log('step3: T_gt shape=%s' % str(T_gt.shape))
    R_rel = T_est[:3, :3].T @ T_gt[:3, :3]
    log('step4: R_rel computed')
    cos_val = (float(np.trace(R_rel)) - 1.0) / 2.0
    log('step5: cos_val=%r' % cos_val)
    cos_val = max(-1.0, min(1.0, cos_val))
    rot_err_deg = float(np.degrees(np.arccos(cos_val)))
    log('step6: rot_err_deg=%.6f' % rot_err_deg)
    trans_err = float(np.linalg.norm(T_est[:3, 3] - T_gt[:3, 3]))
    log('step7: trans_err=%.6f' % trans_err)
    success = bool(rot_err_deg < 5.0 and trans_err < 0.05)
    log('step8: success=%s' % success)
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
    log('step9: evaluator_result.json written')
    print('EVAL: rot_err_deg=%.6f trans_err=%.6f success=%s' % (rot_err_deg, trans_err, success))
except Exception:
    log('EXCEPTION:\n' + traceback.format_exc())
    sys.exit(1)
