# 00_INDEX — l2_20261007_seed202_blind01

## File Inventory

| File | Purpose |
|---|---|
| `README.md` | This index file |
| `run_manifest.json` | Structured manifest of this run |
| `REPRODUCE.md` | How to reproduce this run from scratch |
| `git_snapshot.txt` | Git commit and file hashes at time of run |
| `L2_FROZEN.md` | L2 freeze declaration (case data and config) |
| `B0_FROZEN.md` | Phase B0 blind run freeze declaration (Agent system) |
| `L1_L2_COMPARISON.md` | Comparison with L1 reference run |
| `SECURITY_FIELD_AUDIT.md` | Security check: no API keys/tokens/secrets |

## Root-Level Scattered Files

The following files exist at the run root directory (before organized
closeout) and are mirrored to their corresponding sub-directories.
Originals are preserved; see `01_AGH/`, `02_AGENT/`, `03_TOOL_CHAIN/`,
`04_CONFIG/`, and `05_VALIDATION/` for the organized copies.

| Root file | Organized location |
|---|---|
| `diagnosis.json` | `02_AGENT/diagnosis.json` |
| `decision_01.json` | `02_AGENT/decision_01.json` |
| `agent_assessment_01.json` | `02_AGENT/agent_assessment_01.json` |
| `agent_final_assessment.json` | `02_AGENT/agent_final_assessment.json` |
| `decision_final.json` | `02_AGENT/decision_final.json` |
| `tool_call_01.json` | `03_TOOL_CHAIN/tool_call_01.json` |
| `observation_01.json` | `03_TOOL_CHAIN/observation_01.json` |
| `parameters.json` | `04_CONFIG/parameters.json` |
| `evaluator_result.json` | `05_VALIDATION/evaluator_result.json` |
| `run_summary.md` | `05_VALIDATION/run_summary.md` |
| `agh_run_log.json` | `01_AGH/agh_run_log.json` |
| `input_summary.json` | `01_AGH/input_summary.json` |

## Sub-directory Structure
- `01_AGH/` — AGH session metadata, diagnosis input, screenshot checklist, AGH evidence README
- `02_AGENT/` — Agent decision chain: diagnosis → decision → assessment (GT-blind)
- `03_TOOL_CHAIN/` — Tool execution: tool_call_01.json, observation_01.json, TOOL_CHAIN.md
- `04_CONFIG/` — Parameter structure: base_scale, Agent policy, derived actuals, tool defaults
- `05_VALIDATION/` — Independent GT evaluation: evaluator_result.json, metrics_summary.json, PHASE_B0_VALIDATION.md, run_summary.md
- `06_VISUALS/` — before.png, after.png, compare.png, metrics_panel.png
- `attempts/attempt_01/` — This attempt's complete evidence (no RETRY occurred, no attempt_02)
