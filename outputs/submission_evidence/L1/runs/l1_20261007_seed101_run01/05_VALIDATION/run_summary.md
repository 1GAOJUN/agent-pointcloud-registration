# L1 Run Summary — l1_seed_101 (Phase A / L1 Evidence Closeout)

Generated from real run evidence only. All values below are taken from the files
cited in `run_manifest.json` and `TOOL_CHAIN.md`, not from chat or memory.

## Input
- Source cloud: `outputs/ICP/L1/L1/seed_101/source.ply`, 30,000 points
- Target cloud: `outputs/ICP/L1/L1/seed_101/target.ply`, 30,000 points
- Synthetic L1 case, seed=101: rotation 8/-12/10 deg, translation (0.3, 0.1, 0.2),
  zero noise, zero outliers, zero crop (per `meta.json` in the same directory).
- Agent saw only anonymized `source_cloud` / `target_cloud`; full file paths and
  the L1/L2/L3/L4 label were withheld from the Agent's decision prompt.

## Diagnosis (what the Agent received)
From `diagnosis.json` / `agh_evidence/diagnosis_input.json`:
- source_point_count = 30000, target_point_count = 30000
- source_bbox_diagonal = 1.69460, target_bbox_diagonal = 1.69282
- source_median_spacing = target_median_spacing ≈ 0.011133 (density_ratio ≈ 1.0)
- centroid_distance = 0.37611
- base_scale = 0.033892
- overlap_ratio / noise_level / outlier_level / rotation_magnitude_estimate:
  NOT_IMPLEMENTED (honestly declared as such in the diagnosis)

## Agent Decision
- Selected method: `GLOBAL_FPFH_RANSAC_ICP` (source: `decision_01.json`,
  confirmed identical in `decision_final.json`)
- Candidate methods offered: `GLOBAL_FPFH_RANSAC_ICP`, `LOCAL_ICP`
- Reasoning (from `decision_01.json`, translated): large initial-value offset
  (centroid_distance ≈ 0.376 >> base_scale ≈ 0.034, ratio ≈ 11x), classified as a
  "harder" scene, so a global alignment path was used as the safe default.
- Confidence recorded by the Agent: 0.6
- Note: this decision was made by a deterministic heuristic standing in for a
  real Agnes LLM call inside `src/agent_runner.py` (module docstring explicitly
  says "此实现为可审计的启发式"); it is NOT a demonstration that an LLM itself
  picked this method, and no claim of "LLM-optimized algorithm selection" should
  be drawn from this run.

## Parameters
Agent-chosen policy (relative scale multipliers, not absolute values):
- `global_corr_scale = 5.0`
- `icp_max_corr_scale = 2.0`

Derived actual thresholds (computed in `run_global_fpfh_ransac_icp`,
`src/agent_tools.py`):
- RANSAC max_correspondence_distance = base_scale × 5.0 = 0.16946
- ICP max_correspondence_distance = base_scale × 2.0 = 0.06778

Both values confirmed against the actual returned metrics in
`observation_01.json` (`ransac_max_correspondence_distance` and
`icp_max_correspondence_distance` match exactly).

## Tool Execution
- Tool: `GLOBAL_FPFH_RANSAC_ICP`
- Entrypoint: `src.agent_tools.run_global_fpfh_ransac_icp`
- SOR (nb_neighbors=30, std_ratio=1.0) → normal estimation → FPFH features
  (≤500 keypoints each side, hybrid search radius = max(base_scale, 0.2) = 0.2)
  → RANSAC feature-matching global init → point-to-plane ICP refinement
  (max_iteration=100).
- Single call, no retry (`agent_retry_count = 0`).

## Observable Result (GT-free, visible to the Agent)
From `observation_01.json`:
- fitness = 1.0
- rmse (= inlier_rmse) = 1.0480573452953922e-16
- ransac_fitness = 1.0, ransac_rmse = 1.3449969344340598e-16
- elapsed_s = 0.7089753000000201 (tool execution time only; excludes Agnes
  decision/assessment latency, which is not recorded as a separate field)
- Estimated transform (4×4): see `metrics_summary.json`

## Agent Assessment
- Decision: **ACCEPT** (from `agent_assessment_01.json`, confirmed in
  `agent_final_assessment.json`)
- Reason (translated): "Observable fitness = 1.0000 already reached the 0.8
  threshold; registration quality judged acceptable."
- No RETRY, no ABORT.

## Independent GT Evaluation (after Agent stopped)
From `evaluator_result.json`:
- rotation_error_deg = 0.0 (threshold: 5.0°)
- translation_error = 1.3877787807814457e-17 (threshold: 0.05)
- success = **PASS**
- Evaluator explicitly reads `gt_transform.npy` only at this stage
  (`gt_evaluator: true`, `gt_path` recorded); the Agent's decision and
  assessment stages never received the GT file or its contents
  (`gt_read: false` in `tool_call_01.json`).

## Conclusion
What this single L1 run demonstrates:
- The full Agent closed loop (diagnose → decide → call tool → observe → assess →
  stop → independent GT check) ran end-to-end and produced a correct
  registration result on this synthetic L1 case.
- The Agent's choice of a heavier, more robust global method was appropriate for
  this particular (large-offset, clean-data) case and produced a near-perfect
  result (rotation error ≈ 0°).
- GT isolation held: the Agent never saw the ground-truth transform during
  decision-making.

What it does **not** demonstrate:
- It does not prove the Agent can automatically pick the optimal algorithm for
  every possible scene, nor that this strategy generalizes to L2/L3/L4 or to
  noisier / partially overlapping data.
- The decision logic in this run was a deterministic heuristic, not a verified
  LLM call (see "Agent Decision" note above); treating it as evidence of true
  LLM-driven adaptive selection would overstate the result.

## Evidence Index
All original files: `outputs/agent_runs/l1_seed_101/` (unchanged).
Organized copy + this closeout package: `outputs/submission_evidence/l1_seed_101/`.
Figures (`before.png`, `after.png`, `compare.png`, `compare_zoomed.png`,
`metrics_panel.png`): `outputs/submission_evidence/l1_seed_101/figures/`,
generated from the real `source.ply`/`target.ply` and the real estimated
transform in `observation_01.json` — no data was modified or re-run for these
images.
