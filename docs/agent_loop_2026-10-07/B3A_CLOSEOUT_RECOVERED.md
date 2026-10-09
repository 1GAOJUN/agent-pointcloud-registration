# B3A_CLOSEOUT_RECOVERED — b3_l1_20261007_seed101_blind02

## Formal Run

`b3_l1_20261007_seed101_blind02`

## Core Experiment

**COMPLETE**

All core experiment artifacts are frozen on disk:
- B3A_PRE_FLIGHT_PASS, B3A_VALIDATION, B3A_FROZEN
- Agnes decisions (3 rounds), PCA probe, Cheap ICP probe
- Registration tool call, Agent assessment
- Independent GT Evaluator
- RUN_INDEX entry (PASS)

## Formal Result

| Item | Value |
|---|---|
| Selected Method | GLOBAL_FPFH_RANSAC_ICP |
| Parameter Policy | global_corr_scale=5.0, icp_max_corr_scale=2.0 |
| Agent Observable Fitness | 1.0 |
| Agent Observable RMSE | 0.001423 |
| Runtime | 287.8 s |
| Agent Final Decision | **ACCEPT** (confidence 0.99) |
| GT rotation error | 0.9483° (threshold 5.0° → PASS) |
| GT translation error | 0.000837 (threshold 0.05 → PASS) |
| GT Success | **True** |
| **Run Status** | **PASS** |

## Transport Incident

Occurred during Evidence/Visualization Closeout, **after** core experiment completion.
AGH session dropped before `metrics_panel.png` was written.
No core experiment re-run was required or performed.
See: `B3A_TRANSPORT_INCIDENT.md`

## Missing Artifact

`06_VISUALS/metrics_panel.png`

## Recovery

Reconstructed offline from existing frozen evidence:
- `00_INDEX/metrics_summary.json`
- `04_CONFIG/parameters.json`
- `02_AGENT/agent_final_assessment.json`
- `02_AGENT/evaluator_result.json`

No re-computation of transforms, no re-registration, no re-invocation of Agnes.
Generated via PIL (matplotlib Agg backend unavailable in current environment).

**Recovery script**: `scripts/recover_b3a_metrics_panel.py`

## Core Experiment Re-run

**NO**

## Agnes Re-invoked

**NO**

## Registration Re-run

**NO**

## GT Evaluator Re-run

**NO**

## Frozen Evidence Modified

**NO** — only the missing `metrics_panel.png` and incident/recovery records were added.
All pre-existing evidence files remain untouched.

## Existing Visualizations Preserved

| File | Size | SHA-256 |
|---|---|---|
| before.png | 189 537 | 71E10BED79E1F56B2EB5AB0B1C0BE8BBE1FCA50480C2B92E43F336074D9BD1FE |
| after.png | 191 538 | 52DD9A7A85ECF388F07A9B90102B3C1B19C028A2C272128A89992687C75BADA1 |
| compare.png | 85 267 | 14BBDD39EE0390F0AFAA16898D11F69831A6F367F0522F93099AF7608D7BA57D |
| metrics_panel.png (new) | 45 642 | — |

## Status

B3A L1 Frozen Blind Validation is **fully sealed**.
Proceed to B3B in a new AGH session using the B3 freeze manifest.
