# PHASE B0 L2 Freeze Manifest (L2_FROZEN.md)

This run is the **first L2 blind frozen run** in this project. The following facts
are frozen at the start of execution and must not be changed afterwards.

## Frozen Inputs
- Case: anonymous L2 case, seed=202, data dir `outputs/ICP/L2/L2/seed_202/`
- `source.ply` / `target.ply` each have 30,000 points (clean synthetic data)
- `gt_transform.npy` present, **not read by Agent decision/assessment phase**
- Agnes model: `agnes-3.0-flash`, version `2026-10-06`

## Frozen System (from PHASE_B0_FREEZE_MANIFEST.json)
All four frozen files (agent_runner.py, agent_tools.py, agent_diagnose.py,
agent_evaluator.py) were verified by SHA-256 hash before the run started.

## Frozen L2 Config (configs/L2.yaml)
- rot_x_deg: 75.0, rot_y_deg: 120.0, rot_z_deg: 150.0
- translation: [0.20, 0.40, 0.30]
- n_points: 30000, seed: 202
- thresholds: rot_max_deg=5.0, fitness_min=0.8

## Agent-Visible Diagnosis (from diagnosis.json)
| Field | Value |
|---|---|
| source_point_count | 30000 |
| target_point_count | 30000 |
| centroid_distance | 0.5591 |
| density_ratio | ~1.0 |
| base_scale | 0.03389 |

## Agent Decisions
- Selected method (attempt 01): `GLOBAL_FPFH_RANSAC_ICP`
- Parameter policy: `{global_corr_scale: 5.0, icp_max_corr_scale: 2.0}`
- Derived: ransac_max_corr = 0.16943, icp_max_corr = 0.06777
- Agent decision: `ACCEPT` (fitness = 1.0 ≥ 0.8)
- No RETRY occurred.

## GT Result (read only after Agent stopped)
- rotation_error_deg = 1.7075472925031877e-06 deg
- translation_error = 0.0
- success = `True` → **PASS**
