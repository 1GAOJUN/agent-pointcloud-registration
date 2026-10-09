# TOOL_CHAIN.md — l2_20261007_seed202_blind01

## Step 1: Diagnosis
- **Entry**: `src/agent_diagnose.py: diagnose(source_ply, target_ply)`
- **Output**: `diagnosis.json` — structured metrics (point counts, centroid_distance,
  density_ratio, base_scale, etc.)
- **GT read**: No

## Step 2: Agnes Decision
- **Entry**: `src/agent_runner.py: agnes_decide(diagnosis, TOOL_REGISTRY, prior_attempts)`
- **Input**: `diagnosis.json` + `TOOL_REGISTRY` (static metadata, no code execution)
- **Output**: `decision_01.json` — `selected_method=GLOBAL_FPFH_RANSAC_ICP`,
  `parameter_policy={global_corr_scale:5.0, icp_max_corr_scale:2.0}`
- **GT read**: No
- **Agnes-visible fields only**: observation_summary, diagnosis, candidate_methods,
  selected_method, parameter_policy, reasoning_summary, confidence

## Step 3: Tool Execution
- **Entry**: `src/agent_tools.py: run_global_fpfh_ransac_icp(source_ply, target_ply,
  global_corr_scale=5.0, icp_max_corr_scale=2.0, base_scale=0.03389)`
- **Derived values**:
  - `ransac_max_correspondence_distance = base_scale * global_corr_scale = 0.03389 * 5.0 ≈ 0.16943`
  - `icp_max_correspondence_distance = base_scale * icp_max_corr_scale = 0.03389 * 2.0 ≈ 0.06777`
- **Output**: `observation_01.json` — `transform` (4×4), `fitness=1.0`, `rmse=1.22e-16`,
  `ransac_fitness=1.0`, `ransac_rmse=1.44e-16`, `elapsed_s=0.618`
- **GT read**: No

## Step 4: Agnes Assessment
- **Entry**: `src/agent_runner.py: agnes_assess(observation)`
- **Input**: `observation_01.json` (fitness, rmse, elapsed_s — no GT fields)
- **Output**: `agent_assessment_01.json` — `decision=ACCEPT`,
  `reason="可观测 fitness=1.0000 已达阈值 0.8，判定配准质量可接受。"`
- **GT read**: No

## Step 5: GT Evaluator (independent, after Agent stop)
- **Entry**: `src/agent_evaluator.py: evaluate_agent_result(final_transform, gt_npy)`
- **Input**: final `transform` matrix + `gt_transform.npy`
- **Output**: `evaluator_result.json` — `rot_err_deg=1.71e-06`, `trans_err=0.0`,
  `success=True`
- **GT read**: **Yes** (this is the only allowed GT read point)

## Loop
- max_retry = 2
- Actual attempts = 1 (first attempt ACCEPT → loop terminated)
- No RETRY branch executed
