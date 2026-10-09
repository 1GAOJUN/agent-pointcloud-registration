# B0_FROZEN.md — Phase B0 L2 Blind Run Freeze Declaration

## run_id
`l2_20261007_seed202_blind01`

## Freeze Status
**FINAL_STATUS = PASS**

## Frozen Scope
This run was a **frozen blind run**: the Agent system (agent_runner.py,
agent_tools.py, agent_diagnose.py, agent_evaluator.py) was not modified
between Phase A (L1 seed_101) and this L2 run. SHA-256 hashes of all four
files are recorded in `PHASE_B0_FREEZE_MANIFEST.json` and `git_snapshot.txt`.

## What is frozen (must NOT be modified after this run)
- `02_AGENT/decision_01.json` — Agent's actual decision
- `02_AGENT/agent_assessment_01.json` — Agent's actual assessment
- `03_TOOL_CHAIN/tool_call_01.json` — Actual tool invocation record
- `03_TOOL_CHAIN/observation_01.json` — Actual tool output
- `04_CONFIG/parameters.json` — Actual parameters used
- `05_VALIDATION/evaluator_result.json` — GT evaluation result
- `05_VALIDATION/metrics_summary.json` — Combined metrics summary
- `06_VISUALS/` — All four PNG files
- `attempts/attempt_01/` — Complete attempt_01 evidence
- `L2/RUN_INDEX.csv` — This run's row
- `PHASE_B0_FREEZE_MANIFEST.json` — Freeze manifest

## Future B1/B2 constraint
Even if B1 or B2 modifies the Agent (Prompt, diagnosis, tool descriptions,
algorithm selection policy, parameter policy), **this run's evidence must
remain exactly as recorded here**. No file in this directory may be
overwritten, deleted, or "improved" after the fact.

Any B1/B2 run that changes the Agent system must:
- Generate a **new run_id** (e.g. `l2_YYYYMMDD_seed202_runNN`)
- Write to a **new** `runs/<new_run_id>/` directory
- **Never touch** `runs/l2_20261007_seed202_blind01/`

## Limitation Statement (must not be overstated)
This run proves:
1. The Phase A Agent framework can complete a L2-scale registration task on
   anonymous input without L2-specific knowledge.
2. GT isolation was maintained (no GT leaked to Agent during decision phase).
3. The result is PASS (rot_err=1.71e-06 deg, trans_err=0.0).

This run does **NOT** prove:
- That the Agent demonstrates genuine scenario-adaptive algorithm selection.
  L1 and L2 both used the same method (`GLOBAL_FPFH_RANSAC_ICP`) and the
  same parameter policy (`{global_corr_scale: 5.0, icp_max_corr_scale: 2.0}`).
  The LOCAL_ICP fast-path branch was never triggered in either case.
- That the Agent would behave differently on L3/L4 cases.
