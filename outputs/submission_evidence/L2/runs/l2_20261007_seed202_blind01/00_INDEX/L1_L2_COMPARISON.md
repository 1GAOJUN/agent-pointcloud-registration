# L1 / L2 Comparison — Agent Closed-Loop Blind Runs

## Basic comparison table

| Dimension | L1 (l1_seed_101) | L2 (l2_seed_202_blind01) |
|---|---|---|
| Case seed | 101 | 202 |
| Point count | 30000 each | 30000 each |
| Rotation (config) | small-angle (8°/-12°/10°) | large-angle (75°/120°/150°) |
| Data quality | clean | clean |
| centroid_distance | 0.376 | 0.559 |
| density_ratio | ~1.0 | ~1.0 |
| base_scale | 0.03389 | 0.03389 |
| Agent selected_method | `GLOBAL_FPFH_RANSAC_ICP` | `GLOBAL_FPFH_RANSAC_ICP` |
| Parameter policy | `{global_corr_scale: 5.0, icp_max_corr_scale: 2.0}` | `{global_corr_scale: 5.0, icp_max_corr_scale: 2.0}` |
| RETRY count | 0 | 0 |
| Agent confidence | 0.6 | 0.6 |
| fitness (observable) | 1.0 | 1.0 |
| RMSE | 1.05e-16 | 1.22e-16 |
| Runtime (s) | 0.709 | 0.618 |
| GT rotation error | 0.0 deg | 1.71e-06 deg |
| GT translation error | 1.39e-17 | 0.0 |
| GT success | PASS | PASS |
| Agent decision | ACCEPT | ACCEPT |

## 1. Did L1 and L2 use the same method?
**Yes.** Both selected `GLOBAL_FPFH_RANSAC_ICP` by the same heuristic branch in
`agnes_decide`: centroid_distance / base_scale = 0.559/0.03389 ≈ 16.5 > 3.0 threshold
→ "difficult scenario" → pick GLOBAL. L1 was centroid_distance = 0.376/0.03389 ≈ 11.1 > 3.0
→ also GLOBAL. Same branch, same method, identical parameter policy.

## 2. Did parameters differ?
**No.** The `parameter_policy` values (`global_corr_scale: 5.0, icp_max_corr_scale: 2.0`)
are identical because the heuristic assigns the same fixed policy to the same branch.
The derived absolute values differ only because `base_scale` differs slightly per case
(L1 base_scale = 0.03389 vs L2 = 0.03389 — actually nearly identical).

## 3. Did L2 trigger different closed-loop behaviour?
**No.** L2 behaved exactly like L1: one attempt, immediate ACCEPT, no RETRY.
The Agent's `RETRY` branch was never reached for L2. There was no observable
divergence in closed-loop behaviour between the two levels.

## 4. Can we prove the Agent is scenario-adaptive?
**Partially, but not conclusively.**
- The Agent adapted its **diagnosis reading** to the observed metrics (high centroid_distance
  → hard scenario → GLOBAL). This is a form of input-adaptivity, not level-label knowledge.
- However, both L1 and L2 triggered the **same branch** in the heuristic because
  both had centroid_distance > 3× base_scale. The "small-angle easy → LOCAL_ICP"
  branch was **never exercised** by either L1 or L2.
- **L3 or L4** would be needed to test whether the Agent changes its decision path
  on cases where centroid_distance < 3× base_scale AND density_ratio is balanced → LOCAL_ICP.
- The current evidence **cannot prove** the Agent behaves differently for genuinely
  easy vs. hard cases in a way that constitutes true scenario adaptation, because
  only one of two possible heuristic branches was tested.

## 5. What observation is currently missing?
- **Rotation magnitude estimate** (`rotation_magnitude_estimate` is `NOT_IMPLEMENTED`).
  Without it, the Agent cannot distinguish "small angle but large translation"
  (where LOCAL_ICP might suffice) from "large rotation" (where GLOBAL is required).
  Adding a rotation-magnitude proxy would enable a sharper LOCAL_ICP fast-path
  without needing to guess from centroid_distance alone.
- **Overlap ratio** (`overlap_ratio` is `NOT_IMPLEMENTED`) — for L3/L4 dirty/low-overlap
  cases this is essential for the Agent to know whether GLOBAL will even succeed.
