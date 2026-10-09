# B3B_VALIDATION

**Run:** `b3_l2_20261007_seed202_blind01`
**Phase:** B3B
**Date:** 2026-10-07

---

## Leakage & Integrity Audit

### 1. GT Leakage — PASS

- `gt_transform.npy` was read **only** by `tests/_b3b_evaluator.py` (stage 8, post-Agent-stop).
- No Agnes decision prompt, probe observation, or assessment prompt contains any GT value.
- Verified: `agnnes_raw_decision_01/02/03.json`, `agnnes_raw_assessment.json`,
  `probe_observation_01/02.json` — no `gt_transform`, `rotation_error`, `translation_error` fields.

### 2. Level Label Leakage — PASS

- Agnes-visible inputs (`input_summary.json`, `diagnosis.json`, all decision/assessment prompts)
  contain no `L1`/`L2`/`L3`/`L4` label strings.
- Case label used in all Agnes-facing files: `case_unknown_B` only.

### 3. Seed Semantic Leakage — PASS

- No `seed_202`, `seed`, or seed value appears in any Agnes-visible file.
- `diagnosis.json` contains `sampling_seed: 101` (the fixed PCA/diagnosis sampling seed,
  part of the frozen B2B implementation, not the data-generation seed 202). This is a
  deterministic implementation constant, not a case-semantic leak. The data-generation
  seed 202 itself never appears in any Agnes-visible file.

### 4. Disk Path Leakage — PASS

- No absolute filesystem path (`D:\...`, `outputs/ICP/...`) appears in any Agnes-visible
  file. All Agnes-facing cloud references are the anonymous labels
  `source_cloud` / `target_cloud` with `(path withheld from Agent)`.
- Real paths are used only by Python execution scripts (`tests/_b3b_*.py`) and the
  evaluator — never passed to Agnes.

### 5. Historical Result Leakage — PASS

- No B0 L2 result, B3A result, or any prior-run metric appears in any Agnes-visible file.
- `prior_attempts` in all decision prompts: `[]` (empty; no RETRY occurred this run).

### 6. B3A Result Leakage — PASS

- B3B was executed in a fresh AGH session. No B3A evidence file was read during B3B.
- No B3A run output appears in any B3B Agnes-visible file.

### 7. Python Method Selection — PASS (no Python auto-selection)

- `selected_method` in `agnnes_raw_decision_03.json` = `GLOBAL_FPFH_RANSAC_ICP`
  — produced by real Agnes (subagent_fork), not by `heuristic_decide`.
- No `offset_proxy >= 3 → GLOBAL` fixed mapping was executed in this run.
- `agent_final_assessment.json._implementation` = `"agnnes_real"` (not `"heuristic_baseline"`).

### 8. Python Probe Selection — PASS (no Python auto-trigger)

- Probe order `PCA_ORIENTATION → CHEAP_LOCAL_ICP` appears in two separate Agnes raw
  decision files (`agnnes_raw_decision_01.json` requested_probe=PCA_ORIENTATION,
  `agnnes_raw_decision_02.json` requested_probe=CHEAP_LOCAL_ICP).
- Python performed whitelist + dedup + quota validation only
  (`agnnes_agent.validate_decision`). No diagnosis-metric → probe trigger branch exists
  in `src/agent_probes.py` or `src/agnnes_agent.py` (verified by B2B freeze hash match).

### 9. Python ACCEPT Selection — PASS (no Python auto-accept)

- `agnnes_raw_assessment.json` `decision` = `ACCEPT` (Agnes confidence 0.97).
- Guardrail check: `fitness=1.0 ≥ FLOORGUARD_FITNESS=0.3` → no overwrite applied.
  `_guardrail_applied` field is **absent** from `agnnes_assessment_parsed.json`,
  confirming the decision came from Agnes, not a guardrail overwrite.

### 10. Real Agnes Invocation — PASS

- Four separate Agnes calls were made via `subagent_fork` (round 1, round 2, round 3
  decisions + 1 assessment). Raw outputs saved to `01_AGH/agnnes_raw_*.json`.
- Each raw output was parsed through `agnnes_agent.parse_agnnes_decision` /
  `agnes_assess_from_raw`, which stamps `_implementation: "agnnes_real"` and
  `_agnnes_model: "agnes-3.0-flash"`.

### 11. Freeze Integrity — PASS

- All 9 frozen file hashes recomputed at pre-flight and matched
  `B3_SYSTEM_FREEZE_MANIFEST.json` (see `B3B_PRE_FLIGHT_PASS.md`).
- No frozen source file was modified during B3B execution.

---

## Summary Table

| Check | Result |
|-------|--------|
| GT leakage | PASS |
| Level label leakage | PASS |
| Seed semantic leakage | PASS |
| Disk path leakage | PASS |
| Historical result leakage | PASS |
| B3A result leakage | PASS |
| Python method selection (no auto-select) | PASS |
| Python probe selection (no auto-trigger) | PASS |
| Python ACCEPT selection (no auto-accept) | PASS |
| Real Agnes invocation | PASS |
| Freeze integrity | PASS |

**All 11 checks PASS → B3B_VALIDATION: PASS**
