# B3B_CORE_FROZEN

**Run ID:** `b3_l2_20261007_seed202_blind01`
**Phase:** B3B — Real Agnes + Active Probe, Anonymous Difficult-Pose Frozen Blind Validation
**Anonymous case label:** `case_unknown_B`
**Core completion timestamp (UTC):** 2026-10-07T13:01:36Z

---

## Core Experiment Status: FROZEN

Once this file is written, the core B3B experiment is complete. No subsequent
visualization, transport failure, or closeout step may trigger a re-run of the
core pipeline (diagnosis → Agnes decisions → probes → registration → assessment
→ GT evaluator).

## Agent Final Decision

- **Decision:** `ACCEPT` (Agnes raw confidence 0.97, no guardrail overwrite)
- **Method:** `GLOBAL_FPFH_RANSAC_ICP`
- **Parameter policy (Agnes-chosen):** `{global_corr_scale: 4.0, icp_max_corr_scale: 1.0}`
- **Attempt count:** 1 (no RETRY; `attempts/attempt_01/` only)

## Probe Chain (all requested by real Agnes, verified order)

| Round | Probe | Result |
|-------|-------|--------|
| 1 | `PCA_ORIENTATION` | `rotation_estimate_deg=null`, `orientation_confidence=LOW`, `near_line_degeneracy` (both clouds) |
| 2 | `CHEAP_LOCAL_ICP` | `initial_fitness=0.1366`, `probe_fitness=0.1650`, `fitness_improvement=0.0284`, `transform_delta_magnitude=0.2222`, 5 iterations |

Probe order (PCA → CHEAP_LOCAL_ICP) chosen by two independent real Agnes
decisions; Python performed whitelist/dedup/quota validation only.

## Estimated Transform (path)

`02_AGENT/observation_01.json` → field `transform` (4×4, saved as list of lists)

```
[[ 0.4330127, -0.8538539,  0.2888486,  0.2],
 [-0.2500000,  0.1941143,  0.9485882,  0.4],
 [-0.8660254, -0.4829629, -0.1294095,  0.3],
 [ 0.0,        0.0,        0.0,        1.0]]
```

## Independent GT Evaluator Result (path)

`05_VALIDATION/evaluator_result.json`

| Metric | Value |
|--------|-------|
| `rotation_error_deg` | **0.0** |
| `translation_error`  | **0.0** |
| `success`            | **true** |
| `rot_thr_deg`        | 5.0 |
| `trans_thr`          | 0.05 |

GT transform was read **only** by the evaluator, strictly after the Agent
stopped with `ACCEPT`. No GT value reached any Agnes decision or assessment
prompt.

## Evidence Files (frozen)

- `01_AGH/agnnes_raw_decision_01/02/03.json` — raw Agnes decision outputs
- `01_AGH/agnnes_raw_assessment.json` — raw Agnes assessment output
- `02_AGENT/agnnes_decision_01/02/03_parsed.json` — guardrail-validated decisions
- `02_AGENT/agnnes_assessment_parsed.json` — guardrail-validated assessment
- `02_AGENT/probe_observation_01/02.json` — probe observations
- `02_AGENT/observation_01.json`, `decision_final.json`, `metrics.json`
- `03_TOOL_CHAIN/tool_call_01.json`
- `04_CONFIG/parameters.json`
- `05_VALIDATION/evaluator_result.json`
- `attempts/attempt_01/` — full attempt-01 evidence copy

## No RETRY / No Failed Attempts

`attempts/` contains only `attempt_01/`. No RETRY was requested by Agnes; no
failed attempt was generated or deleted.
