"""Stable E0 launcher: AGH/Real Agnes callbacks wired into the existing runner.

This module contains transport and argument wiring only. It never selects a
probe, registration method, parameter policy, or terminal verdict.
"""

from __future__ import annotations

import argparse
import inspect
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
REQUIRED_PYTHON = Path(r"D:\APP\Anaconda\envs\pointcloud_agh\python.exe")
AGH_ENTRY = Path(r"D:\STUDY\darker\agnes-harness\packages\cli\dist\local\agnes.mjs")
VALID_VARIANTS = ("REAL_AGNES_NO_PROBE", "REAL_AGNES_ACTIVE_PROBE")

sys.path.insert(0, str(PROJECT_ROOT / "src"))

import agent_runner  # noqa: E402
from agnnes_agent import AgnesDecisionAdapter  # noqa: E402


def _same_path(left: Path, right: Path) -> bool:
    return str(left.resolve()).casefold() == str(right.resolve()).casefold()


def _extract_model_text(record: dict[str, Any]) -> str | None:
    for key in ("text", "output", "result", "content", "assistant", "assistantText", "modelText"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    return None


class AgnesCliCallbacks:
    """Transport-only callbacks. Every professional response comes from AGH/Agnes."""

    def __init__(self, variant: str) -> None:
        self.variant = variant
        self.calls: list[dict[str, Any]] = []

    def _invoke(self, prompt: str, phase: str) -> str:
        if not AGH_ENTRY.is_file():
            raise RuntimeError(f"AGH CLI entry not found: {AGH_ENTRY}")
        variant_note = (
            "This is REAL_AGNES_NO_PROBE. Active Probe is unavailable for this ablation variant. "
            "Set information_sufficient=true and requested_probe=NONE, then make the method and "
            "parameter decision yourself from the supplied GT-free evidence.\n\n"
            if phase == "decision" and self.variant == "REAL_AGNES_NO_PROBE"
            else ""
        )
        if phase == "decision":
            phase_instruction = (
                "This is a strategy Decision call. Return the Decision schema only. "
                "A Probe request uses information_sufficient=false, requested_probe set to a registered "
                "Probe, and selected_method=null. A formal method choice uses information_sufficient=true, "
                "requested_probe=NONE, and a non-null selected_method. Do not return an Assessment schema. "
            )
        else:
            phase_instruction = (
                "This is a post-registration Assessment call. Return the Assessment schema only. "
                "The required decision field must be exactly ACCEPT, RETRY, or ABORT. "
                "Do not request a Probe and do not return information_sufficient, requested_probe, "
                "selected_method, or any Decision-schema object. "
            )
        instruction = (
            "You are the Real Agnes component in a formal point-cloud registration run. "
            + phase_instruction
            + "Use only the supplied JSON. Do not read files, paths, scene labels, seeds, or Ground Truth. "
              "Return exactly one JSON object matching output_schema, with no prose or code fence.\n\n"
        )
        # Standalone is required by the current local-dev profile for provider routing.
        # A unique workspace gives each callback a fresh AGH session, preventing a
        # previous Decision response from being replayed as an Assessment response.
        with tempfile.TemporaryDirectory(prefix="e0-agh-callback-") as callback_cwd:
            proc = subprocess.run(
                [
                    "node", str(AGH_ENTRY), "-p", "--mode", "json", "--standalone",
                    "--profile", "local-dev", "--cwd", callback_cwd,
                ],
                input=instruction + variant_note + prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(PROJECT_ROOT),
            )
        record = None
        for line in (proc.stdout or "").splitlines():
            try:
                candidate = json.loads(line.strip())
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(candidate, dict) and candidate.get("v") == "agnes-cli-result/v1":
                record = candidate
        if proc.returncode != 0:
            raise RuntimeError(
                f"AGH {phase} callback failed with exit code {proc.returncode}: "
                f"{(proc.stderr or '').strip()[:1000]}")
        if record is None:
            raise RuntimeError(f"AGH {phase} callback returned no agnes-cli-result/v1 record")
        text_payload = _extract_model_text(record)
        if not text_payload:
            raise RuntimeError(f"AGH {phase} callback returned no model text")
        self.calls.append({
            "phase": phase,
            "session_id": record.get("sessionId"),
            "model": record.get("model"),
            "exit_code": proc.returncode,
        })
        return text_payload

    def decision(self, prompt: str) -> str:
        return self._invoke(prompt, "decision")

    def assessment(self, prompt: str) -> str:
        return self._invoke(prompt, "assessment")


def _derive_gt_path(source: Path) -> Path:
    if source.parent.name != "agent_input":
        raise ValueError("source must be inside an anonymous case agent_input directory")
    gt = source.parent.parent / "evaluator_only" / "gt_transform.npy"
    if not gt.is_file():
        raise FileNotFoundError(f"evaluator-only transform not found: {gt}")
    return gt


def _smoke_test() -> int:
    if not _same_path(Path(sys.executable), REQUIRED_PYTHON):
        raise RuntimeError(f"wrong Python: {sys.executable}; required: {REQUIRED_PYTHON}")
    state: dict[str, list[Any]] = {"probes_already_run": [], "probe_observations": []}
    adapter = AgnesDecisionAdapter(
        get_raw_decision=lambda _prompt: "{}",
        get_raw_assessment=lambda _prompt: "{}",
        probes_already_run_fn=lambda: state["probes_already_run"],
        probe_observations_fn=lambda: state["probe_observations"],
    )
    signature = inspect.signature(agent_runner.run_agent_case)
    required = {"variant", "probe_state", "agnes_decide_fn", "agnes_assess_fn"}
    missing = required.difference(signature.parameters)
    if missing or not callable(adapter.decide) or not callable(adapter.assess):
        raise RuntimeError(f"wiring smoke failed; missing={sorted(missing)}")
    print(json.dumps({
        "status": "PASS",
        "python": sys.executable,
        "runner": str(signature),
        "formal_run_started": False,
    }, ensure_ascii=False))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one E0 Real Agnes formal loop")
    parser.add_argument("--variant", choices=VALID_VARIANTS)
    parser.add_argument("--source")
    parser.add_argument("--target")
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir")
    parser.add_argument("--smoke-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.smoke_test:
        return _smoke_test()
    missing = [name for name in ("variant", "source", "target", "run_id", "output_dir")
               if not getattr(args, name)]
    if missing:
        raise SystemExit(f"missing required arguments: {', '.join(missing)}")
    if not _same_path(Path(sys.executable), REQUIRED_PYTHON):
        raise RuntimeError(f"wrong Python: {sys.executable}; required: {REQUIRED_PYTHON}")

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not source.is_file() or not target.is_file():
        raise FileNotFoundError("source or target point cloud does not exist")
    if source.parent != target.parent or source.parent.name != "agent_input":
        raise ValueError("source and target must share one anonymous agent_input directory")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing Run directory: {output_dir}")
    if output_dir.name != args.run_id:
        raise ValueError("output-dir basename must equal run-id")

    gt_path = _derive_gt_path(source)
    state: dict[str, list[Any]] = {"probes_already_run": [], "probe_observations": []}
    callbacks = AgnesCliCallbacks(args.variant)
    adapter = AgnesDecisionAdapter(
        get_raw_decision=callbacks.decision,
        get_raw_assessment=callbacks.assessment,
        probes_already_run_fn=lambda: state["probes_already_run"],
        probe_observations_fn=lambda: state["probe_observations"],
    )
    result = agent_runner.run_agent_case(
        source_ply=str(source),
        target_ply=str(target),
        run_dir=str(output_dir),
        gt_npy=str(gt_path),
        agnes_decide_fn=adapter.decide,
        agnes_assess_fn=adapter.assess,
        variant=args.variant,
        probe_state=state,
        run_id=args.run_id,
    )
    (output_dir / "agh_callback_sessions.json").write_text(
        json.dumps(callbacks.calls, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
