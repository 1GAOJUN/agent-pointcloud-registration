# TOOL_CHAIN — l1_seed_101

Actual tool-call chain for this L1 run. Every step is traceable to a file in
`outputs/agent_runs/l1_seed_101/` (originals) and the mirrored copy under
`outputs/submission_evidence/l1_seed_101/raw/`.

```
Step 1  diagnosis
        File: diagnosis.json  (identical content in agh_evidence/diagnosis_input.json)
        Content: GT-free metrics only — point counts, bbox diagonal, median
                 spacing, density_ratio, centroid_distance, base_scale,
                 initial_transform_available. overlap_ratio / noise_level /
                 outlier_level / rotation_magnitude_estimate are declared
                 "NOT_IMPLEMENTED", not guessed.

        ↓

Step 2  Agnes decision
        File: decision_01.json  (final copy: decision_final.json)
        Content: selected_method = GLOBAL_FPFH_RANSAC_ICP
                 parameter_policy = {global_corr_scale: 5.0, icp_max_corr_scale: 2.0}
                 candidate_methods = [GLOBAL_FPFH_RANSAC_ICP, LOCAL_ICP]
                 confidence = 0.6
                 reasoning: initial offset large relative to base_scale -> use
                            global alignment as safe default.
        Note:  produced by the deterministic heuristic standing in for an LLM
               call (see agent_runner.py module docstring); flagged in
               run_summary.md so it is not overstated.

        ↓

Step 3  tool call
        File: tool_call_01.json
        Content: step=1, tool_name=GLOBAL_FPFH_RANSAC_ICP
                 entrypoint=src.agent_tools.run_global_fpfh_ransac_icp
                 inputs.source = source_cloud (anonymized, real file:
                                  outputs/ICP/L1/L1/seed_101/source.ply)
                 inputs.target = target_cloud (anonymized, real file:
                                  outputs/ICP/L1/L1/seed_101/target.ply)
                 inputs.base_scale = 0.033892031543267295
                 inputs.parameter_policy = {global_corr_scale: 5.0,
                                            icp_max_corr_scale: 2.0}
                 gt_read = false  ← explicit proof the tool path does not touch GT
        Returned metric keys (declared, not values):
                 transform, fitness, rmse, ransac_fitness, ransac_rmse,
                 elapsed_s, ransac_max_correspondence_distance,
                 icp_max_correspondence_distance, tool_name,
                 parameter_policy_used

        ↓

Step 4  observation (actual tool return values)
        File: observation_01.json
        Content:
                 transform = [[0.9632873407929414, -0.20045436175063014, -0.17859324713776506, 0.3],
                              [0.16985354835670544, 0.9701990375235616, -0.17281087841623471, 0.09999999999999999],
                              [0.2079116908177593, 0.13613183479077168, 0.9686283355228664, 0.2],
                              [0.0, 0.0, 0.0, 1.0]]
                 fitness = 1.0
                 rmse = 1.0480573452953922e-16
                 ransac_fitness = 1.0
                 ransac_rmse = 1.3449969344340598e-16
                 elapsed_s = 0.7089753000000201
                 ransac_max_correspondence_distance = 0.1694601577163365
                 icp_max_correspondence_distance = 0.06778406308653459
                 tool_name = GLOBAL_FPFH_RANSAC_ICP
                 parameter_policy_used = {global_corr_scale: 5.0, icp_max_corr_scale: 2.0}

        ↓

Step 5  Agnes assessment
        File: agent_assessment_01.json  (final copy: agent_final_assessment.json)
        Content: decision = ACCEPT
                 reason: observable fitness = 1.0000 ≥ threshold 0.8
                 next_action = {}  (no retry needed)

        ↓  (Agent loop stops here — no RETRY, agent_retry_count = 0)

Step 6  Independent Evaluator reads GT (only now, only here)
        File: evaluator_result.json
        Content: gt_evaluator = true
                 rot_err_deg = 0.0
                 trans_err = 1.3877787807814457e-17
                 success = true
                 rot_thr_deg = 5.0, trans_thr = 0.05
                 gt_path = outputs/ICP/L1/L1/seed_101/gt_transform.npy
                 timestamp = 2026-10-06 17:31:28
        Code reference: src/agent_evaluator.py::evaluate_agent_result
        (docstring + code both state GT is read only at this stage)

        ↓

Step 7  Final result: PASS
        rotation error 0.0° < 5.0°  ✓
        translation error ≈ 1.4e-17 < 0.05  ✓
```

## Cross-file consistency checks performed during closeout
1. `diagnosis.json` vs `agh_evidence/diagnosis_input.json`: byte-identical.
2. `decision_01.json` vs `decision_final.json`: byte-identical (single attempt,
   no RETRY, so "final" decision = first decision).
3. `agent_assessment_01.json` vs `agent_final_assessment.json`: byte-identical.
4. The estimated transform in `observation_01.json`, when applied to the real
   `source.ply` centroid [0.01337778, -0.02556248, 0.01074667], lands exactly on
   the real `target.ply` centroid [0.31609147, 0.07561442, 0.20971106]
   (verified by independent re-computation, matching `diagnosis.json`'s
   centroid_distance = 0.37611058938785075 exactly).
5. `evaluator_result.json` timestamp (17:31:28) is later than the runner's
   execution timestamp (17:31:24 UTC, 17:31:28 local +08:00) recorded in
   `agh_run_log.json`/README, consistent with "Evaluator runs after Agent
   stops".

## Where each piece lives
- Originals: `outputs/agent_runs/l1_seed_101/*.json` and
  `outputs/agent_runs/l1_seed_101/agh_evidence/*`
- Mirrored copies used for this submission:
  `outputs/submission_evidence/l1_seed_101/raw/*.json` and
  `outputs/submission_evidence/l1_seed_101/raw/agh_evidence/*`
- Original run files are **not** modified by this closeout; they remain in
  their original location unchanged.
