# Formal Blind Registration Task Template

Run label: `<new_anonymous_run_id>`

Use Agnes through an AGH Web session to execute the existing Real Agnes + Active Probe workflow on:

- source: `<anonymous_source_cloud_path>`
- target: `<anonymous_target_cloud_path>`

Rules:

1. Do not inspect dataset labels, generation metadata, evaluator-only files, historical Agent answers, or any reference transform.
2. Agnes owns all Probe, registration method, parameter-policy, and `ACCEPT` / `RETRY` / `ABORT` decisions.
3. Treat diagnosis, Probe results, correspondence-support observations, and prior Attempts as observations—not deterministic method-selection rules.
4. Preserve every Attempt and retain the existing retry guardrail.
5. Stop the Agent before independent evaluation. Evaluation occurs only after the Agent has stopped.
6. Save formal Evidence using the required Level → Run → Attempt structure under `outputs/submission_evidence/`.

Do not execute this template until the anonymous input package and required observation are ready.
