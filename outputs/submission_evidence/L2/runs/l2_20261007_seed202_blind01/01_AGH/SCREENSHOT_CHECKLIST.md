# AGH SCREENSHOT CHECKLIST — l2_20261007_seed202_blind01

## What to screenshot (by hand, after this run)

**Note:** Official raw AGH session trace is NOT exportable to the repo.
This checklist lists the most valuable **web-UI moments** to capture manually.
Do NOT fabricate any image. Only capture what is actually on screen.

---

### Screenshot 1: Agnes First Decision (Decision Output)
- **When**: After the Agent closed-loop run completed and you can see
  the `decision_01.json` content in AGH's conversation
- **What to show**: The structured JSON with `selected_method`, `parameter_policy`,
  `observation_summary`, `confidence`, `reasoning_summary`
- **Model**: agnes-3.0-flash
- **Time**: ~2026-10-07 (UTC time of this run)
- **What it proves**: Agnes actually produced the decision from diagnosis,
  not pre-loaded or hardcoded

### Screenshot 2: Tool Call / Observation
- **When**: After the tool execution step in the conversation, when the
  `observation_01.json` content (fitness, rmse, ransac_fitness, transform) is visible
- **What to show**: The fitness=1.0, rmse≈1.2e-16, elapsed_s≈0.62,
  `tool_name: GLOBAL_FPFH_RANSAC_ICP`
- **What it proves**: The tool actually ran and returned real observable metrics

### Screenshot 3: Final Agent Assessment / ACCEPT
- **When**: After `agent_assessment_01.json` shows `decision: "ACCEPT"`
- **What to show**: The ACCEPT verdict and reason ("fitness=1.0 ≥ 0.8")
- **What it proves**: Agent made a genuine stop-decision based on observable
  criteria, not pre-programmed to accept

### Screenshot 4: GT Evaluator Result (optional but valuable)
- **When**: After `evaluator_result.json` is visible showing
  `rot_err_deg=1.71e-06`, `trans_err=0.0`, `success=true`
- **What it proves**: Independent GT verification was performed AFTER
  Agent stopped (GT isolation confirmed)

---

## Where to save screenshots
Save to: `runs/l2_20261007_seed202_blind01/01_AGH/screenshots/`
Name them: `screenshot_01_decision.png`, `screenshot_02_tool_observation.png`,
`screenshot_03_accept.png`, `screenshot_04_gt_evaluator.png` (optional)

**Do not** put placeholder text files in place of real screenshots.
If you skip a moment, note it in this file as "not captured".
