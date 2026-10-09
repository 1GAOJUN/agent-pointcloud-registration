# PHASE B0 L2 Blind Run — Validation Checks

## Check items

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | **GT leakage**: Agent decision/assessment did not read GT | PASS | `tool_call_01.json` shows `gt_read: false`; `evaluator_result.json` is the only file that reads GT; Agent phase has no GT field access in code |
| 2 | **Level label leakage**: No L1/L2/L3/L4 label in Agent prompt | PASS | `input_summary.json` uses only `source_cloud` / `target_cloud` anonymous names; no level string appears in `decision_01.json` |
| 3 | **Path leakage**: No disk path in Agent prompt | PASS | `input_summary.json` says `path withheld from Agent`; Agent sees only point counts and diagnostic metrics |
| 4 | **Method hint leakage**: No prompt phrase suggesting which tool to pick | PASS | Prompt only describes available tools with applicable conditions and limitations; heuristic branch is in code, not prompt text |
| 5 | **L2-specific parameter**: No hardcoded L2-only branch in source | PASS | All four frozen source files verified by SHA-256 hash; no `if level == L2` or similar branch exists in any `src/agent_*.py` file |
| 6 | **Python bypassing Agnes**: Agent runner is the sole decision path | PASS | `run_agent_case` is the only entry; all decisions come from `agnes_decide()` which is the frozen Phase A heuristic |
| 7 | **Agnes actually called**: Agnes decision chain is present | PASS | `decision_01.json`, `agent_assessment_01.json`, `agent_final_assessment.json` all exist and are non-trivial; `agh_run_log.json` records the chain |
| 8 | **Same runner as L1**: Agent runner file identical | PASS | SHA-256 of `src/agent_runner.py` = `40bf497a...` matches Phase A L1 frozen hash |
| 9 | **Policy unchanged before blind run**: No source modification during L2 run | PASS | All four frozen files hash-verified before run; `git status` shows only new evidence dirs as untracked, no src/ changes |

## Summary
All 9 checks: **PASS**
No cheating indicators found. The L2 blind run used the identical Phase A Agent system
with no modifications.
