# DEV-X.1 Tool-bearing Smoke

You are running inside Agnes Harness (AGH). Perform exactly this safe development check:

1. Call the AGH `write` tool to create `outputs/development/headless_agh/DEVX_TOOL_SMOKE_MARKER.txt` with the exact UTF-8 text `DEVX_TOOL_SMOKE_OK` followed by one newline.
2. Call the AGH `read` tool on that same file.
3. Report whether the observed content exactly matches.

Do not call `shell`, Probe, Registration, or Evaluator. Do not read ground truth. Do not access or modify `outputs/submission_evidence/B3/`. Do not touch any path outside this project.
