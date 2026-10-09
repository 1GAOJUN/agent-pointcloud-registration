# PHASE B0 L2 Run Summary — l2_20261007_seed202_blind01

## Agent-Visible Information (what Agent could see)
- **Input**: anonymous `source_cloud` (30000 points) and `target_cloud` (30000 points)
- **Diagnosis** (from `agent_diagnose.diagnose`):
  - centroid_distance = 0.5591
  - density_ratio = 1.0 (balanced)
  - base_scale = 0.03389 (≈ source_median_spacing / bbox_diagonal)
  - initial_transform_available = True
- **Available tools**: LOCAL_ICP, GLOBAL_FPFH_RANSAC_ICP (SVD_ICP excluded, EXPERIMENT_ONLY)

## Agent First Decision (attempt_01)
- **Selected method**: `GLOBAL_FPFH_RANSAC_ICP`
- **Reason**: `centroid_distance / base_scale ≈ 16.5 > 3.0` → Agent heuristic classified this
  as a "hard scenario" → pick GLOBAL tool
- **Parameter policy**: `{global_corr_scale: 5.0, icp_max_corr_scale: 2.0}`
- **Derived values** (from actual run):
  - `ransac_max_correspondence_distance = 0.16943`
  - `icp_max_correspondence_distance = 0.06777`
- **Agent confidence**: 0.6

## Attempt 01 Result
- `fitness = 1.0`, `rmse = 1.22e-16`, `elapsed_s = 0.618`
- **Agent assessment**: `ACCEPT` (fitness ≥ 0.8 threshold)
- **Reason**: "可观测 fitness=1.0000 已达阈值 0.8，判定配准质量可接受。"

## Retry Process
- **No RETRY occurred.** The Agent accepted on the first attempt.
- `attempts/attempt_02/` does not exist because it was never triggered.

## Final Agent Judgment
- **Decision**: `ACCEPT`
- **Method used**: `GLOBAL_FPFH_RANSAC_ICP`
- **Number of attempts**: 1

## GT Final Validation (Evaluator, read AFTER Agent stopped)
- **rotation_error_deg** = `1.7075472925031877e-06` deg
- **translation_error** = `0.0`
- **success** = `True` (threshold: rot < 5.0°, trans < 0.05)
- **Final status**: **PASS**

## Notes
- The Agent's heuristic branch "centroid_distance > 3× base_scale → GLOBAL tool"
  is the same branch that fired in L1 seed_101 (L1 centroid_distance = 0.376,
  L2 = 0.559; both > 3× base_scale). No L2-specific behaviour was triggered;
  the run is structurally identical to L1 in terms of Agent decision path.
- The run confirms GLOBAL_FPFH_RANSAC_ICP successfully handles large-rotation
  (75°/120°/150°) cases where plain ICP (unit-matrix init) would fail.
