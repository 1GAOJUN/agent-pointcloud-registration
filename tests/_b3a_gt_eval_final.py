import json, numpy as np
from pathlib import Path

ROOT = Path(r'D:\STUDY\darker\agent-pointcloud-registration')
run_dir = ROOT / 'outputs' / 'submission_evidence' / 'B3' / 'L1' / 'runs' / 'b3_l1_20261007_seed101_blind02'
agent_dir = run_dir / '02_AGENT'

obs = json.loads((agent_dir / 'observation_01.json').read_text(encoding='utf-8'))
T_est = np.asarray(obs['transform'], dtype=np.float64)
T_gt = np.load(str(ROOT / 'data' / 'L1' / 'seed_101' / 'gt_transform.npy'))

# rotation error
R_rel = T_est[:3, :3].T @ T_gt[:3, :3]
cos_val = (float(np.trace(R_rel)) - 1.0) / 2.0
cos_val = max(-1.0, min(1.0, cos_val))  # clamp for numerical safety
rot_err_deg = float(np.degrees(np.arccos(cos_val)))

# translation error
t_est = T_est[:3, 3]
t_gt = T_gt[:3, 3]
trans_err = float(np.linalg.norm(t_est - t_gt))

success = bool(rot_err_deg < 5.0 and trans_err < 0.05)

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
print('EVAL: rot_err_deg=%.6f trans_err=%.6f success=%s' % (rot_err_deg, trans_err, success))
