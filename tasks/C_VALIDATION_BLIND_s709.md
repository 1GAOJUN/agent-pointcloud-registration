# Formal Blind Validation Task

Run label: `c_unknown_20261008_s709_blind01`

Use Agnes through AGH Web to run the existing Real Agnes + Active Probe workflow on only:

- source: `data/formal_blind/case_unknown_C_20261008_s709/agent_input/source_cloud.ply`
- target: `data/formal_blind/case_unknown_C_20261008_s709/agent_input/target_cloud.ply`

Agnes alone decides probes, registration method, parameter policy, and ACCEPT/RETRY/ABORT. Use the current decision and assessment prompt builders, and save this Run's own prompt snapshots under its `01_AGH/` evidence. Do not inspect sibling directories, generation metadata, historical answers, or evaluator-only material. Preserve every Attempt and stop the Agent before independent evaluation.
