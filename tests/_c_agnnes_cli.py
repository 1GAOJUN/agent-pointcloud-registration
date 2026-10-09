"""Phase C: capture fresh Agnes LLM decision via headless AGH CLI (fallback for subagent_fork contamination).

Usage:
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_c_agnnes_cli.py <decision_round|assessment_attempt_NN> <prompt_or_observation_file>

Reads the relevant prompt JSON from the given file (01_AGH/agnnes_decision_prompt_NN.json or
01_AGH/agnnes_assessment_prompt_attempt_NN.json), builds the full prompt text, invokes a fresh
AGH session (node agnes.mjs -p --mode json, prompt via stdin), parses the model's text payload,
and writes the raw response to 01_AGH/agnnes_raw_decision_NN.json (or agnnes_raw_assessment_attempt_NN.json).
GT is NOT read.
"""
import sys, json, time, subprocess
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
run_dir = ROOT / "outputs" / "submission_evidence" / "C" / "runs" / "c_unknown_20261008_s707_blind01"
agh_dir = run_dir / "01_AGH"

which = sys.argv[1] if len(sys.argv) > 1 else "decision_1"

# Parse which round/attempt
if which.startswith("decision_"):
    round_no = int(which.split("_")[1])
    prompt_file = agh_dir / f"agnnes_decision_prompt_{round_no:02d}.json"
    out_file = agh_dir / f"agnnes_raw_decision_{round_no:02d}.json"
    instruction = (
        "TASK: You are a 3D point-cloud registration expert choosing a registration strategy for one "
        "decision round of a point cloud registration agent. Read ONLY the JSON prompt below. Do NOT "
        "search files, do NOT read Ground Truth / rotation / translation / level labels / seeds, do NOT "
        "use the internet. All information is inside the JSON. Reply with a single JSON object matching "
        "the output_schema in the prompt. No code fences, no prose.\n\n"
    )
    prompt_payload = prompt_file.read_text(encoding="utf-8")
elif which.startswith("assessment_"):
    part = which.split("_", 2)
    attempt_no = int(part[2].lstrip("attempt_"))
    prompt_file = agh_dir / f"agnnes_assessment_prompt_attempt_{attempt_no:02d}.json"
    out_file = agh_dir / f"agnnes_raw_assessment_attempt_{attempt_no:02d}.json"
    instruction = (
        "TASK: You are a 3D point-cloud registration expert assessing a registration attempt's "
        "observable result. Decide ACCEPT / RETRY / ABORT based ONLY on the observable metrics "
        "(fitness, rmse, ransac metrics, elapsed_s, tool name, parameter policy) in the JSON prompt. "
        "Do NOT search files. Do NOT read Ground Truth / rotation error / translation error / level "
        "labels / seeds (none is provided, none may be guessed). Reply with a single JSON object "
        "matching output_schema in the prompt. No code fences, no prose.\n\n"
    )
    prompt_payload = prompt_file.read_text(encoding="utf-8")
else:
    print(f"[ERROR] unsupported which={which}")
    sys.exit(1)

if not prompt_file.exists():
    print(f"[ERROR] prompt file missing: {prompt_file}")
    sys.exit(1)

full_prompt = instruction + prompt_payload
print(f"[OK] prompt bytes: {len(full_prompt.encode('utf-8'))}")

# Locate the AGH CLI entry: prefer the 'local' alias (kept in sync with the active AGH instance),
# falling back to the most recent timestamped build under agnes-harness.
agh_cli_root = Path(r"D:\STUDY\darker\agnes-harness\packages\cli\dist")
local_alias = agh_cli_root / "local" / "agnes.mjs"
if local_alias.exists():
    entry = local_alias
else:
    candidates = [d for d in sorted(agh_cli_root.iterdir(), key=lambda p: p.name, reverse=True)
                  if d.is_dir() and (d / "agnes.mjs").exists()]
    if not candidates:
        print(f"[ERROR] no AGH CLI entry under {agh_cli_root}")
        sys.exit(2)
    entry = candidates[0] / "agnes.mjs"
print(f"[OK] using AGH CLI entry: {entry}")

t0 = time.time()
proc = subprocess.run(
    ["node", str(entry), "-p", "--mode", "json", "--standalone",
     "--profile", "local-dev", "--cwd", str(ROOT)],
    input=full_prompt, capture_output=True, text=True, encoding="utf-8", errors="replace")
wall = time.time() - t0
print(f"[OK] agnes CLI exit={proc.returncode} wall={wall:.2f}s")
if proc.stderr:
    print("--- stderr (first 800 chars) ---")
    print(proc.stderr[:800])

# The last agnes-cli-result/v1 JSON record in stdout carries the model's text output
raw_stdout = proc.stdout or ""
record = None
for line in raw_stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        continue
    if rec.get("v") == "agnes-cli-result/v1":
        record = rec

if record is None:
    out_file.write_text(json.dumps({"_error": "no agnes-cli-result record", "stdout": raw_stdout[:4000]},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
    print("[ERROR] no agnes-cli-result record found; see saved partial")
    sys.exit(3)

# Extract the model text payload (field name may vary across CLI versions; keep whole record + likely text fields)
text_payload = None
for key in ("text", "output", "result", "content", "assistant", "assistantText", "modelText"):
    if isinstance(record.get(key), str):
        text_payload = record[key]
        break

result = {
    "model": "agnes-3.0-flash",
    "invocation": "agh_headless_cli_fresh_session",
    "entry": str(entry),
    "session_id": record.get("sessionId"),
    "cli_exit_code": proc.returncode,
    "wall_s": round(wall, 3),
    "prompt_bytes": len(full_prompt.encode("utf-8")),
    "record": record,
    "text_payload": text_payload,
}
out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"[OK] raw captured to {out_file.name}")
print("--- text_payload ---")
print(text_payload)
