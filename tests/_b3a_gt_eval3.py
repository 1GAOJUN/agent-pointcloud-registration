import json, numpy as np, traceback, sys
from pathlib import Path
ROOT = Path(r'D:\STUDY\darker\agent-pointcloud-registration')
try:
    print('A', file=sys.stderr)
    obs = json.loads((ROOT/'outputs'/'submission_evidence'/'B3'/'L1'/'runs'/'b3_l1_20261007_seed101_blind02'/'02_AGENT'/'observation_01.json').read_text(encoding='utf-8'))
    print('B', file=sys.stderr)
    T_est = np.asarray(obs['transform'], dtype=np.float64)
    print('C', file=sys.stderr)
    T_gt = np.load(str(ROOT/'data'/'L1'/'seed_101'/'gt_transform.npy'))
    print('D', file=sys.stderr)
    R_rel = T_est[:3,:3].T @ T_gt[:3,:3]
    rot_err = float(np.degrees(np.arccos(np.clip((np.trace(R_rel)-1)/2, -1, 1))))
    print('E', file=sys.stderr)
    trans_err = float(np.linalg.norm(T_est[:3,3] - T_gt[:3,3]))
    print('F rot=%.6f trans=%.6f' % (rot_err,trans_err), file=sys.stderr)
    result = {
        'gt_evaluator': True,
        'note': 'GT read only after Agent stop (ACCEPT).',
        'rot_err_deg': rot_err,
        'trans_err': trans_err,
        'success': bool(rot_err < 5.0 and trans_err < 0.05),
        'rot_thr_deg': 5.0,
        'trans_thr': 0.05,
        'gt_path': str(ROOT/'data'/'L1'/'seed_101'/'gt_transform.npy'),
    }
    (ROOT/'outputs'/'submission_evidence'/'B3'/'L1'/'runs'/'b3_l1_20261007_seed101_blind02'/'02_AGENT'/'evaluator_result.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('G done', file=sys.stderr)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
