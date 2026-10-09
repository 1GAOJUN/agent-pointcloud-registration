# Phase D Readiness Audit

## Scope

Read-only audit of the existing partial-overlap case and current Agent-visible tools. No formal Run was started and no core code or Evidence was changed.

## Existing case

- Configuration: `configs/L4.yaml`.
- Existing data: `outputs/ICP/L4/L4/seed_404/`.
- Source: 30,000 points; target: 18,139 points; target/source count ratio `0.604633`.
- Pose configuration: rotations `(10, 15, -8)` degrees and translation `(0.30, 0.15, 0.25)`.
- No configured noise or injected outliers.
- Generation transforms the full source, then applies half-space cropping to the target.
- `crop_ratio=0.30` is a fraction of coordinate span used to place a threshold, not a point-count deletion fraction. The non-uniform geometry therefore produces about 39.54% point removal in this case.
- Implementation detail: `_crop_half_space` currently maps configured `z` to coordinate index 0. The existing bytes are therefore genuinely partial-overlap data, but the actual crop direction does not match the configuration label. This must be recorded as provenance if this case is frozen; it does not require an algorithm change for readiness.

## Current Agent-visible evidence

Basic Diagnosis already exposes:

- source/target point counts and `point_count_ratio`;
- source/target bounding-box diagonals and `bbox_diagonal_ratio`;
- robust nearest-neighbor spacing, density ratio, and isolated-point proxies;
- centroid distance and base scale.

For the existing case, the relevant observations are point-count ratio `0.604633`, bounding-box ratio `0.875782`, density ratio `0.774231`, and centroid distance `0.594809`. The explicit `overlap_ratio` field remains `NOT_IMPLEMENTED`.

PCA Orientation can still provide a coarse orientation signal, subject to its documented ambiguity handling. Cheap Local ICP supplies initial/probe fitness, RMSE, improvement, and transform delta. Its `correspondence_count` is currently null, but Open3D fitness is already a one-direction normalized correspondence-support signal at the configured distance threshold. `LOCAL_ICP` and `GLOBAL_FPFH_RANSAC_ICP` can both run unchanged; the global tool is documented as usable at lower overlap, although extremely low overlap remains a limitation.

## Readiness judgment

The existing tool chain is executable, but direct formal use is not yet well-observed enough for a defensible partial-overlap decision. Point-count imbalance is not itself an overlap estimate, and a one-direction fitness can hide asymmetric coverage.

The single necessary development item is a low-cost, deterministic, GT-free **bidirectional correspondence-support proxy** at a documented distance threshold, surfaced as Observation only. It should report source-to-target and target-to-source support (or their symmetric summary) and must not select a method or verdict. No new registration algorithm is indicated.

Estimated development scope: **SMALL**.

