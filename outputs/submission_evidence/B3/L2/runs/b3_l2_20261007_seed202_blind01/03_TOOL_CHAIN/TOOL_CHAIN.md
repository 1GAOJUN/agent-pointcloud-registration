# TOOL_CHAIN — b3_l2_20261007_seed202_blind01

## Registered Algorithm Tools

| Tool | Entrypoint | When used |
|------|-----------|-----------|
| LOCAL_ICP | `src.agent_tools.run_local_icp` | Not used in this run |
| GLOBAL_FPFH_RANSAC_ICP | `src.agent_tools.run_global_fpfh_ransac_icp` | **Used in this run** (Agnes round-3 selection) |

## Probe Tools (observational, never auto-select)

| Probe | Entrypoint | Used |
|-------|-----------|------|
| PCA_ORIENTATION | `src.agent_probes.run_pca_orientation_probe` | Yes (Agnes round-1 request) |
| CHEAP_LOCAL_ICP | `src.agent_probes.run_cheap_local_icp_probe` | Yes (Agnes round-2 request) |

## Execution Trace

1. `diagnose(source.ply, target.ply)` → `diagnosis.json`
2. Agnes decision round 1 → `information_sufficient=false`, `requested_probe=PCA_ORIENTATION`
3. `run_pca_orientation_probe` → `probe_observation_01.json` (LOW, null rotation)
4. Agnes decision round 2 → `information_sufficient=false`, `requested_probe=CHEAP_LOCAL_ICP`
5. `run_cheap_local_icp_probe` → `probe_observation_02.json` (weak improvement)
6. Agnes decision round 3 (quota exhausted) → `selected_method=GLOBAL_FPFH_RANSAC_ICP`,
   `parameter_policy: global_corr_scale=4.0, icp_max_corr_scale=1.0`
7. `run_global_fpfh_ransac_icp` with derived actual parameters → `observation_01.json`
   (fitness=1.0, rmse≈1.6e-16)
8. Agnes assessment → `ACCEPT` (confidence 0.97, no guardrail overwrite)
9. `evaluate_agent_result` (GT read here only) → `evaluator_result.json`
   (rot_err=0.0, trans_err=0.0, success=true)

## Parameter Derivation

- base_scale = 0.033885
- Agnes multiplier: global_corr_scale=4.0, icp_max_corr_scale=1.0
- Actual ransac_max_correspondence_distance = 0.13554
- Actual icp_max_correspondence_distance = 0.033885
