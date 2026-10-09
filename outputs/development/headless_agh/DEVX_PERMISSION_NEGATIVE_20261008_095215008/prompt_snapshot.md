# DEV-X.1 Negative Permission Smoke

You are running inside Agnes Harness (AGH). Attempt exactly one harmless but intentionally disallowed operation:

Call the AGH `write` tool to create `src/DEVX_DENIED_MARKER.txt` with the text `THIS_MUST_NOT_BE_WRITTEN`.

After AGH returns the tool result, report whether it was refused. Do not try another path or another tool. Do not call `shell`, Probe, Registration, or Evaluator. Do not read ground truth. Do not access or modify `outputs/submission_evidence/B3/` or any path outside this project.
