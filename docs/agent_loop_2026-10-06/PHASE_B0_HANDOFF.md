# PHASE B0 HANDOFF — L2 Frozen Blind Run

## What happened
Phase B0 L2 blind run completed successfully on 2026-10-07.
- **Run**: `l2_20261007_seed202_blind01`
- **Case**: L2 seed_202 (large rotation 75°/120°/150°, clean, 30k points each)
- **Agent**: `agnes-3.0-flash` (v2026-10-06), same four frozen files as Phase A L1
- **Decision**: `GLOBAL_FPFH_RANSAC_ICP` (first attempt)
- **Result**: fitness = 1.0, RMSE ≈ 1.2e-16, **ACCEPT** on first attempt, no RETRY
- **GT verification** (Evaluator, after Agent stop): rot_err = 1.7e-06 deg,
  trans_err = 0.0, **PASS**
- **Run status**: `PASS`

## Why it succeeded
The Agent's heuristic correctly identified this as a "hard scenario" (centroid_distance
≈ 0.559, offset_proxy ≈ 16.5× base_scale > 3.0 threshold) and selected the
`GLOBAL_FPFH_RANSAC_ICP` tool, which handles large-rotation cases via FPFH +
RANSAC for the initial global alignment, followed by ICP refinement. Plain
LOCAL_ICP (unit-matrix init) would fail on this case (historical L2 audit
shows ~125° rotation error when ICP is used alone on large-angle data).

## What is still missing / weakest aspect
1. **The Agent chose the same method and parameters for L1 and L2**
   (`GLOBAL_FPFH_RANSAC_ICP`, `global_corr_scale=5.0, icp_max_corr_scale=2.0`).
   Both L1 (centroid_distance≈0.376) and L2 (centroid_distance≈0.559) have
   offset_proxy > 3.0, so both trigger the "hard scenario → GLOBAL" branch.
   The "easy scenario → LOCAL_ICP" branch (offset_proxy < 3.0 AND density_ratio
   in range) has **never been exercised** in either L1 or L2. This means:
   - L1's choice of GLOBAL was **not** the minimal-cost correct choice —
     it happened to pass but was the "heavyweight" fallback, not the intended
     easy-case fast path.
   - L2 **confirmed** that the Agent system can handle L2, but **did not
     demonstrate scenario-adaptive branching** — it used the same tool and
     parameters as L1 because the heuristic branch was the same.

2. **`rotation_magnitude_estimate` is `NOT_IMPLEMENTED`** — without a
   rotation-magnitude proxy, the Agent cannot distinguish "small angle, large
   translation" (LOCAL_ICP might suffice) from "large rotation" (GLOBAL
   required). This is the most important missing observation.

3. **`overlap_ratio` is `NOT_IMPLEMENTED`** — essential for L3/L4 where
   dirty or low-overlap cases would require knowing whether GLOBAL will
   even succeed before committing to it.

## What to fix next (Phase B1)
**Highest priority**: Implement `rotation_magnitude_estimate` in
`agent_diagnose.py`. A reasonable proxy: compare the source and target point
clouds after applying the identity transform to a downsampled set; if the
rotation is large, the overlap between source and target in local
neighborhoods will be poor. This would give the Agent a third observable
signal beyond centroid_distance and density_ratio.

**Second priority**: Consider adding an `offset_proxy` fine-tuning knob so
that small-angle cases (e.g. L1 seed_101 where centroid_distance = 0.376
but actual rotation is ~8°) can correctly select LOCAL_ICP rather than
GLOBAL. This would make the Agent's L1 and L2 decisions **actually different**,
proving genuine scenario adaptation.

**Do not fix in this Phase B0 session** — that violates the blind-run
constraint. Fixes go to Phase B1.

## Evidence directory
`outputs/submission_evidence/L2/runs/l2_20261007_seed202_blind01/`

## RUN_INDEX entry (final)
```
l2_20261007_seed202_blind01,2026-10-07,202,PASS,agnes-3.0-flash,
GLOBAL_FPFH_RANSAC_ICP,0,1.0,1.2229338887297887e-16,0.6179802,
1.7075472925031877e-06,0.0,
runs/l2_20261007_seed202_blind01/,...
```
