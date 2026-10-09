# REPRODUCE.md — l2_20261007_seed202_blind01

## How to reproduce this run
```bash
# Prerequisite: Open3D 0.20.0 in conda env `pointcloud_agh`
cd D:\STUDY\darker\agent-pointcloud-registration
conda activate pointcloud_agh

# Run the Agent closed-loop on L2 seed_202 case
python src/agent_runner.py l2_20261007_seed202_blind01 \
  outputs/ICP/L2/L2/seed_202/source.ply \
  outputs/ICP/L2/L2/seed_202/target.ply \
  outputs/ICP/L2/L2/seed_202/gt_transform.npy
```

## Expected results
- diagnosis: source=30000, target=30000, centroid_distance≈0.5591, base_scale≈0.03389
- selected_method: GLOBAL_FPFH_RANSAC_ICP (Agent decides via heuristic, not L2 label)
- parameter policy: {global_corr_scale: 5.0, icp_max_corr_scale: 2.0}
- fitness=1.0, rmse≈1.2e-16, elapsed_s≈0.62
- Agent decision: ACCEPT (fitness ≥ 0.8)
- No RETRY
- GT: rot_err≈1.7e-06 deg, trans_err=0.0, success=True → PASS

## Key files
- Raw run: `outputs/agent_runs/l2_20261007_seed202_blind01/`
- Organized evidence: `outputs/submission_evidence/L2/runs/l2_20261007_seed202_blind01/`
- Case data: `outputs/ICP/L2/L2/seed_202/`
- L2 config: `configs/L2.yaml`
