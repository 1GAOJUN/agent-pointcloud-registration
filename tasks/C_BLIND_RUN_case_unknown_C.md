# Formal Blind Registration Task

Run label: `c_unknown_20261008_s707_blind01`

Use Agnes through the AGH Web session to perform the existing Real Agnes + Active Probe workflow on these anonymous inputs:

- source: `data/formal_blind/case_unknown_C_20261008_s707/agent_input/source_cloud.ply`
- target: `data/formal_blind/case_unknown_C_20261008_s707/agent_input/target_cloud.ply`

Rules:

1. Read only the two input clouds and current tool schemas during the Agent stage. Do not inspect sibling directories, dataset metadata, historical Agent answers, or evaluator-only material.
2. Agnes must make all probe, registration method, parameter policy, and ACCEPT/RETRY/ABORT decisions. Python may execute registered tools and return observations but must not replace those decisions.
3. Available probes are `PCA_ORIENTATION` and `CHEAP_LOCAL_ICP`. Available registration tools are `LOCAL_ICP` and `GLOBAL_FPFH_RANSAC_ICP`.
4. Preserve every Attempt. If Agnes returns RETRY, feed the preceding Attempt observation and assessment into the next decision, subject to the existing retry guardrail.
5. Stop the Agent before any independent evaluation. Evaluation is a separate post-stop stage.
6. Save formal evidence under `outputs/submission_evidence/C/runs/c_unknown_20261008_s707_blind01/` using the Level → Run → Attempt structure.

Return the AGH session identifier and the final Agent decision when the Agent stage stops.
