# SECURITY FIELD AUDIT — L1 Evidence Package

Audit date: 2026-10-07 (L1 Evidence Structure Upgrade round)
Scope audited:
- `outputs/submission_evidence/L1/` (all files, pre- and post- this round's move)
- `PHASE_A_STATE.json` / `PHASE_A_HANDOFF.md` (in `docs/agent_loop_2026-10-06/`,
  referenced by the task but not part of the evidence package itself — checked
  anyway for completeness)
- `run_manifest.json` (in `00_INDEX/`)
- All evidence README / chain / summary Markdown files under the L1 package

## Search terms
`session_key`, `conversation_key`, `api_key` / `apikey`, `token`, `secret`
(and the variant `agh_session_key` used in our own manifest field naming)

## Findings

### 1. API Key / Token / Secret
**Not found anywhere** in `outputs/submission_evidence/L1/` or in the
PHASE_A handoff files. No credential of any kind was ever written into the
evidence package, its README, or into Git.

### 2. `session_key` occurrences — disposition
| File | Field | Value pattern | Sensitive? | Action taken |
|---|---|---|---|---|
| `PHASE_A_STATE.json` | `session_key` | a UUID-like AGH runtime session identifier | No — plain, non-secret conversation/session id, not an API credential | Not part of the frozen evidence package (lives in `docs/`, not `outputs/submission_evidence/`); left in place, flagged for the record. Renaming that file's field was **not** part of this task (no re-run, no rewrite of PHASE_A handoff files). |
| `runs/l1_20261007_seed101_run01/00_INDEX/run_manifest.json` | was `agh_session_key` | same UUID value, a plain session id | No | **Renamed to `agh_session_id`** in this round, per the task's rule ("if a session_key is actually just an ordinary non-sensitive conversation ID: rename to session_id"). The `route` / `slot` fields (`agh_route`, `agh_slot`) are plain labels, not secrets, and were kept as-is. |

### 3. `conversation_key` / `api_key` / `token` / `secret`
No occurrences found in any file under `outputs/submission_evidence/` (full
recursive grep across all `.json` / `.md` files before and after this round's
reorganization).

## Result
- **No API key, token or secret is present in the evidence directory, in the
  README, or in any file that would go into Git** — rule 1 is satisfied.
- The one `session_key`-style field that was inside the evidence package
  (`run_manifest.json`'s `agh_session_key`) was confirmed to be a plain,
  non-sensitive AGH runtime session ID and has been **renamed to
  `agh_session_id`**; no value was redacted because none was judged
  secret.
- `run_id`, `model_name` (=`agnes_model`), `model_version`
  (=`agnes_model_version`), and timestamp fields are untouched and remain
  fully present, as required ("不影响 run_id / model_name / model_version /
  timestamp").
- `PHASE_A_STATE.json` (in `docs/`) still uses the old field name
  `session_key`; it was out of scope for renaming this round (no rewrite of
  Phase A handoff documents was requested), but is disclosed here so nobody
  mistakes it for a leaked credential.
