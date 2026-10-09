import json, numpy as np
from pathlib import Path
ROOT = Path(r'D:\STUDY\darker\agent-pointcloud-registration')
agent_dir = ROOT / 'outputs' / 'submission_evidence' / 'B3' / 'L1' / 'runs' / 'b3_l1_20261007_seed101_blind02' / '02_AGENT'
obs = json.loads((agent_dir / 'observation_01.json').read_text(encoding='utf-8'))
T_est = np.asarray(obs['transform'], dtype=np.float64)
T_gt = np.load(str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'))
R_rel = T_est[:3,:3].T @ T_gt[:3,:3]
rot_err = float(np.degrees(np.arccos(np.clip((np.trace(R_rel)-1)/2, -1, 1))))
trans_err = float(np.linalg.norm(T_est[:3,3] - T_gt[:3,3]))
success = bool(rot_err < 5.0 and trans_err < 0.05)
result = {
    'gt_evaluator': True,
    'note': 'GT read only after Agent stop (ACCEPT).',
    'rot_err_deg': rot_err,
    'trans_err': trans_err,
    'success': success,
    'rot_thr_deg': 5.0,
    'trans_thr': 0.05,
    'gt_path': str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'),
}
(agent_dir / 'evaluator_result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print('EVAL: rot_err_deg=%s trans_err=%s success=%s' % (rot_err, trans_err, success))
