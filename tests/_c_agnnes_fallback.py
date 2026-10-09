"""Phase C fallback: capture a fresh Agnes LLM raw response via headless AGH CLI.

Usage:
  & 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' tests/_c_agnnes_fallback.py <out_json_path> <in_json_path>

Wraps node agnes.mjs -p --mode json with the content of in_json_path as the prompt
(UTF-8), saves the raw stdout JSON (the last agnes-cli-result/v1 record carries
textual output) to out_json_path. Fallback only - main path is subagent_fork.
"""
import sys, json, time, subprocess
from pathlib import Path

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")

out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
in_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if not out_path or not in_path:
    print("[ERROR] usage: _c_agnnes_fallback.py <out_json> <in_json>")
    sys.exit(1)

prompt_text = in_path.read_text(encoding="utf-8")

# Locate the AGH CLI entry (most recent build under agnes-harness)
agh_cli_root = Path(r"D:\STUDY\darker\agnes-harness\packages\cli\dist")
candidates = [d for d in sorted(agh_cli_root.iterdir(), key=lambda p: p.name, reverse=True)
              if d.is_dir() and (d / "agnes.mjs").exists()]
if not candidates:
    print(f"[ERROR] no AGH CLI entry under {agh_cli_root}")
    sys.exit(2)
entry = candidates[0] / "agnes.mjs"
print(f"[OK] using AGH CLI entry: {entry}")

t0 = time.time()
proc = subprocess.run(
    ["node", str(entry), "-p", "--mode", "json", "--profile", "local-dev",
     "--cwd", str(ROOT)],
    input=prompt_text, capture_output=True, text=True, encoding="utf-8", errors="replace")
wall = time.time() - t0

print(f"[OK] agnes CLI exit={proc.returncode} wall={wall:.2f}s")
if proc.stderr:
    print("--- stderr (first 500 chars) ---")
    print(proc.stderr[:500])

# The last agnes-cli-result/v1 JSON record in stdout carries the model's text output
raw_text = proc.stdout or ""
record = None
for line in raw_text.splitlines():
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
    out_path.write_text(json.dumps({"_error": "no agnes-cli-result record", "stdout": raw_text[:4000]},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
    print("[ERROR] no agnes-cli-result record found")
    sys.exit(3)

# Extract the model text payload (field name may vary; keep the whole record + text field)
text_payload = None
for key in ("text", "output", "result", "content", "assistant"):
    if isinstance(record.get(key), str):
        text_payload = record[key]
        break
result = {
    "model": "agnes-3.0-flash",
    "invocation": "agh_headless_cli_fallback",
    "session_id": record.get("sessionId"),
    "exit_code": proc.returncode,
    "wall_s": round(wall, 3),
    "prompt_bytes": len(prompt_text.encode("utf-8")),
    "record": record,
    "text_payload": text_payload,
}
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"[OK] raw captured to {out_path}")
print("--- text_payload ---")
print(text_payload)
