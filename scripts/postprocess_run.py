#!/usr/bin/env python3
"""Deterministic, evidence-only post-processing for a completed formal run.

This script never calls Agnes, probes, registration, or the evaluator.  It reads
existing evidence and writes only the documented derived report/visual files.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any, Iterable

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DERIVED_RELATIVE_PATHS = {
    Path("06_VISUALS/before.png"),
    Path("06_VISUALS/after.png"),
    Path("06_VISUALS/compare.png"),
    Path("06_VISUALS/metrics_panel.png"),
    Path("06_VISUALS/overlap_detail.png"),
    Path("00_INDEX/run_summary.md"),
    Path("00_INDEX/ARTIFACT_MAP.md"),
    Path("05_VALIDATION/metrics_summary.json"),
}


def _read_json(path: Path | None) -> Any:
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _first_existing(run_dir: Path, candidates: Iterable[str]) -> Path | None:
    for relative in candidates:
        path = run_dir / relative
        if path.is_file():
            return path
    return None


def _json_files(run_dir: Path, patterns: Iterable[str]) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in run_dir.glob(pattern) if path.is_file())
    return sorted(found, key=lambda path: path.as_posix())


def _path_from_evidence(value: Any, run_dir: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.split(" (", 1)[0].strip()
    path = Path(raw)
    candidates = [path] if path.is_absolute() else [run_dir / path, PROJECT_ROOT / path]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def _walk_path_values(value: Any, keys: set[str]) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in keys:
                yield child
            yield from _walk_path_values(child, keys)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_path_values(child, keys)


def _resolve_cloud(run_dir: Path, kind: str, evidence: list[Any]) -> Path | None:
    names = (f"{kind}.ply", f"{kind}_cloud.ply")
    local = sorted(
        path for path in run_dir.rglob("*.ply")
        if path.name.lower() in names
    )
    if local:
        return local[0].resolve()

    keys = {kind, f"{kind}_path", f"{kind}_ply", f"{kind}_cloud"}
    for document in evidence:
        for value in _walk_path_values(document, keys):
            path = _path_from_evidence(value, run_dir)
            if path and path.suffix.lower() == ".ply":
                return path

    # Historical formal runs record the hidden data directory, or the evaluator's
    # GT path.  Resolve only the sibling cloud named by that recorded evidence;
    # never open the GT file itself.
    for document in evidence:
        if not isinstance(document, dict):
            continue
        bases: list[Path] = []
        hidden = document.get("data_path_hidden_from_agent")
        if isinstance(hidden, str):
            raw = hidden.split(" (", 1)[0].strip()
            base = Path(raw)
            bases.append(base if base.is_absolute() else PROJECT_ROOT / base)
        gt_path = document.get("gt_path")
        if isinstance(gt_path, str):
            raw_gt = Path(gt_path)
            gt_parent = raw_gt.parent if raw_gt.is_absolute() else (PROJECT_ROOT / raw_gt).parent
            bases.append(gt_parent)
            if gt_parent.name.lower() == "evaluator_only":
                bases.append(gt_parent.parent / "agent_input")
        for base in bases:
            for name in names:
                candidate = base / name
                if candidate.is_file():
                    return candidate.resolve()
    return None


def _as_transform(value: Any) -> np.ndarray | None:
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        return None
    return matrix


def _find_transform(evaluator: Any, observations: list[Any], final_transform: Any = None) -> np.ndarray | None:
    if isinstance(final_transform, dict):
        matrix = _as_transform(final_transform.get("transform"))
        if matrix is not None:
            return matrix
    if isinstance(evaluator, dict):
        matrix = _as_transform(evaluator.get("estimated_transform"))
        if matrix is not None:
            return matrix
    for observation in reversed(observations):
        if isinstance(observation, dict):
            matrix = _as_transform(observation.get("transform"))
            if matrix is not None:
                return matrix
    return None


def _attempt_number(path: Path) -> int:
    for part in path.parts:
        if part.lower().startswith("attempt_"):
            try:
                return int(part.split("_", 1)[1])
            except (IndexError, ValueError):
                pass
    return 10**9


def _attempts(run_dir: Path) -> list[dict[str, Any]]:
    root = run_dir / "attempts"
    if not root.is_dir():
        return []
    result: list[dict[str, Any]] = []
    directories = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: (_attempt_number(p), p.name))
    for index, directory in enumerate(directories, 1):
        summary_path = _first_existing(directory, ["attempt_summary.json", f"{directory.name}_summary.json"])
        decision_path = _first_existing(directory, ["decision.json", "decision_final.json"])
        assessment_path = _first_existing(
            directory,
            ["agent_final_assessment.json", "assessment.json", "agent_assessment_01.json", "agnnes_assessment_parsed.json"],
        )
        observation_path = _first_existing(directory, ["observation.json", "observation_01.json"])
        metrics_path = _first_existing(directory, ["metrics.json"])
        parameters_path = _first_existing(directory, ["parameters.json"])
        summary = _read_json(summary_path) or {}
        decision = _read_json(decision_path) or {}
        assessment = _read_json(assessment_path) or {}
        observation = _read_json(observation_path) or {}
        metrics = _read_json(metrics_path) or {}
        parameters = _read_json(parameters_path) or {}
        result.append({
            "attempt": summary.get("attempt_no", index),
            "directory": directory.name,
            "method": summary.get("method", decision.get("selected_method", metrics.get("tool_name", observation.get("tool_name", "UNKNOWN")))),
            "parameter_policy": summary.get("parameter_policy", decision.get("parameter_policy", observation.get("parameter_policy_used", "UNKNOWN"))),
            "derived_parameters": parameters.get("derived_actual_parameters", "UNKNOWN"),
            "fitness": summary.get("fitness", metrics.get("fitness", observation.get("fitness", "UNKNOWN"))),
            "rmse": summary.get("rmse", metrics.get("rmse", observation.get("rmse", "UNKNOWN"))),
            "runtime_s": metrics.get("elapsed_s", observation.get("elapsed_s", observation.get("tool_elapsed_s", "UNKNOWN"))),
            "verdict": summary.get("final_agent_decision", assessment.get("decision", "UNKNOWN")),
            "retried": summary.get("retried", assessment.get("decision") == "RETRY"),
        })
    return result


def _flat_attempts(run_dir: Path) -> list[dict[str, Any]]:
    """Reconstruct numbered Attempts from immutable flat Run evidence."""
    numbers = sorted({
        int(path.stem.rsplit("_", 1)[1])
        for pattern in ("decision_[0-9][0-9].json", "observation_[0-9][0-9].json")
        for path in run_dir.glob(pattern)
    })
    result: list[dict[str, Any]] = []
    for number in numbers:
        suffix = f"{number:02d}"
        decision = _read_json(run_dir / f"decision_{suffix}.json") or {}
        observation = _read_json(run_dir / f"observation_{suffix}.json") or {}
        assessment = _read_json(run_dir / f"agent_assessment_{suffix}.json") or {}
        actual = {
            key: value for key, value in observation.items()
            if "correspondence_distance" in key or key in {"voxel_size"}
        }
        verdict = assessment.get("decision", "UNKNOWN")
        result.append({
            "attempt": number,
            "directory": ".",
            "method": decision.get("selected_method", observation.get("tool_name", "UNKNOWN")),
            "parameter_policy": decision.get("parameter_policy", observation.get("parameter_policy_used", "UNKNOWN")),
            "derived_parameters": actual or "UNKNOWN",
            "fitness": observation.get("fitness", "UNKNOWN"),
            "rmse": observation.get("rmse", observation.get("inlier_rmse", "UNKNOWN")),
            "runtime_s": observation.get("wall_clock_s", observation.get("elapsed_s", "UNKNOWN")),
            "verdict": verdict,
            "retried": verdict == "RETRY",
        })
    return result


def collect_evidence(run_dir: Path) -> dict[str, Any]:
    manifest = _read_json(_first_existing(run_dir, ["00_INDEX/run_manifest.json", "run_manifest.json"]))
    diagnosis = _read_json(_first_existing(run_dir, ["02_AGENT/diagnosis.json", "diagnosis.json"]))
    evaluator = _read_json(_first_existing(run_dir, ["05_VALIDATION/evaluator_result.json", "evaluator_result.json", "02_AGENT/evaluator_result.json"]))
    parameters = _read_json(_first_existing(run_dir, ["04_CONFIG/parameters.json", "parameters.json"]))
    final_transform = _read_json(_first_existing(run_dir, ["final_transform.json"]))
    final_assessment = _read_json(_first_existing(
        run_dir,
        ["02_AGENT/agent_final_assessment.json", "02_AGENT/agnnes_assessment_parsed.json", "agent_final_assessment.json"],
    ))
    preferred_decision_path = _first_existing(
        run_dir,
        ["decision_final.json", "decision_01.json", "02_AGENT/decision_final.json"],
    )
    preferred_decision = _read_json(preferred_decision_path)
    decision_paths = _json_files(run_dir, [
        "decision_*.json", "decision_final.json",
        "02_AGENT/agnnes_decision_*_parsed.json", "02_AGENT/decision_final.json",
        "attempts/*/decision*.json",
    ])
    decisions = [{"file": path.relative_to(run_dir).as_posix(), "value": _read_json(path)} for path in decision_paths]
    decisions = [item for item in decisions if item["value"] is not None]
    observation_paths = _json_files(run_dir, ["observation*.json", "02_AGENT/observation*.json", "attempts/*/observation*.json"])
    observations = [_read_json(path) for path in observation_paths]
    observations = [value for value in observations if value is not None]
    metrics_paths = _json_files(run_dir, ["metrics.json", "02_AGENT/metrics.json", "attempts/*/metrics.json"])
    metrics_all = [_read_json(path) for path in metrics_paths]
    metrics_all = [value for value in metrics_all if value is not None]
    attempts = _attempts(run_dir) or _flat_attempts(run_dir)
    documents = [manifest, diagnosis, evaluator, parameters, final_assessment, *observations, *metrics_all]
    source = _resolve_cloud(run_dir, "source", documents)
    target = _resolve_cloud(run_dir, "target", documents)
    transform = _find_transform(evaluator, observations, final_transform)
    final_observation = observations[-1] if observations else None
    final_metrics = metrics_all[-1] if metrics_all else final_observation

    # Phase C stores a single Attempt as flat Run evidence.  Preserve the same
    # logical Attempt representation without requiring a B3 attempts/ subtree.
    if not attempts and isinstance(final_observation, dict) and isinstance(preferred_decision, dict):
        attempts = [{
            "attempt": 1,
            "directory": ".",
            "method": preferred_decision.get("selected_method", final_observation.get("tool_name", "UNKNOWN")),
            "parameter_policy": preferred_decision.get("parameter_policy", final_observation.get("parameter_policy_used", "UNKNOWN")),
            "derived_parameters": parameters.get("derived_actual_parameters", "UNKNOWN") if isinstance(parameters, dict) else "UNKNOWN",
            "fitness": final_observation.get("fitness", "UNKNOWN"),
            "rmse": final_observation.get("rmse", final_observation.get("inlier_rmse", "UNKNOWN")),
            "runtime_s": final_observation.get("elapsed_s", final_observation.get("wall_clock_s", "UNKNOWN")),
            "verdict": final_assessment.get("decision", "UNKNOWN") if isinstance(final_assessment, dict) else "UNKNOWN",
            "retried": False,
        }]
    elif len(attempts) == 1 and isinstance(final_observation, dict) and isinstance(preferred_decision, dict):
        # Some flat Runs contain only an archival attempt directory skeleton.
        # Fill missing summary cells from that Run's explicit root evidence.
        attempt = attempts[0]
        fallbacks = {
            "method": preferred_decision.get("selected_method", final_observation.get("tool_name", "UNKNOWN")),
            "parameter_policy": preferred_decision.get("parameter_policy", final_observation.get("parameter_policy_used", "UNKNOWN")),
            "fitness": final_observation.get("fitness", "UNKNOWN"),
            "rmse": final_observation.get("rmse", final_observation.get("inlier_rmse", "UNKNOWN")),
            "runtime_s": final_observation.get("elapsed_s", final_observation.get("wall_clock_s", "UNKNOWN")),
            "verdict": final_assessment.get("decision", "UNKNOWN") if isinstance(final_assessment, dict) else "UNKNOWN",
        }
        for key, value in fallbacks.items():
            if attempt.get(key) == "UNKNOWN":
                attempt[key] = value

    required = {
        "source": source,
        "target": target,
        "estimated_transform": transform,
        "diagnosis": diagnosis,
        "Agnes_decisions": decisions,
        "attempts": attempts,
        "observation_or_metrics": final_observation or final_metrics,
        "final_assessment": final_assessment,
        "evaluator_result": evaluator,
        "parameters": parameters,
    }
    def absent(value: Any) -> bool:
        return value is None or (isinstance(value, (list, dict)) and len(value) == 0)

    missing = [name for name, value in required.items() if absent(value)]
    activity = any(not absent(value) for key, value in required.items() if key not in {"source", "target"})
    status = "COMPLETE" if not missing else ("INTERRUPTED" if activity else "INCOMPLETE")
    return {
        "run_id": manifest.get("run_id", run_dir.name) if isinstance(manifest, dict) else run_dir.name,
        "status": status,
        "missing": missing,
        "source": source,
        "target": target,
        "transform": transform,
        "manifest": manifest or {},
        "diagnosis": diagnosis,
        "decisions": decisions,
        "preferred_decision": preferred_decision or {},
        "attempts": attempts,
        "final_observation": final_observation or {},
        "final_metrics": final_metrics or {},
        "final_assessment": final_assessment or {},
        "evaluator": evaluator or {},
        "parameters": parameters or {},
        "probe_observations": [
            value for value in (_read_json(path) for path in _json_files(run_dir, ["probe_*.json"]))
            if value is not None
        ],
    }


def _value(mapping: Any, *keys: str, default: Any = "UNKNOWN") -> Any:
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return default


def _summary_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    metrics = evidence["final_metrics"]
    observation = evidence["final_observation"]
    assessment = evidence["final_assessment"]
    evaluator = evidence["evaluator"]
    parameters = evidence["parameters"]
    final_decision = evidence.get("preferred_decision") or next(
        (item["value"] for item in reversed(evidence["decisions"])
         if isinstance(item["value"], dict) and item["value"].get("selected_method")),
        {},
    )
    return {
        "run_id": evidence["run_id"],
        "status": evidence["status"],
        "missing_items": evidence["missing"],
        "selected_method": _value(final_decision, "selected_method", default=_value(metrics, "tool_name", default=_value(observation, "tool_name"))),
        "parameter_policy": _value(final_decision, "parameter_policy", default=_value(observation, "parameter_policy_used", default=_value(parameters, "agnnes_multiplier"))),
        "derived_parameters": _value(parameters, "derived_actual_parameters"),
        "fitness": _value(metrics, "fitness", default=_value(observation, "fitness")),
        "rmse": _value(metrics, "rmse", "inlier_rmse", default=_value(observation, "rmse", "inlier_rmse")),
        "runtime_s": _value(metrics, "elapsed_s", "runtime_s", default=_value(observation, "elapsed_s", "runtime_s", "tool_elapsed_s")),
        "agent_verdict": _value(assessment, "decision", default=_value(evidence["manifest"], "final_agent_decision")),
        "gt_rotation_error_deg": _value(evaluator, "rot_err_deg", "rotation_error_deg"),
        "gt_translation_error": _value(evaluator, "trans_err", "translation_error"),
        "final_result": _value(evaluator, "success", default="UNKNOWN"),
        "attempt_count": len(evidence["attempts"]),
        "retry_occurred": any(bool(attempt.get("retried")) or attempt.get("verdict") == "RETRY" for attempt in evidence["attempts"]),
        "attempts": evidence["attempts"],
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _markdown(summary: dict[str, Any]) -> str:
    missing = ", ".join(summary["missing_items"]) if summary["missing_items"] else "None"
    lines = [
        f"# Run Summary — {summary['run_id']}", "",
        f"- Status: **{summary['status']}**",
        f"- Missing core evidence: {missing}",
    ]
    if summary["status"] != "COMPLETE":
        lines += ["", "No success result or geometry visualization was generated. Existing partial evidence was preserved.", ""]
        return "\n".join(lines)
    lines += [
        f"- Selected method: `{summary['selected_method']}`",
        f"- Parameter policy: `{json.dumps(summary['parameter_policy'], ensure_ascii=False, sort_keys=True)}`",
        f"- Derived parameters: `{json.dumps(summary['derived_parameters'], ensure_ascii=False, sort_keys=True)}`",
        f"- Fitness: `{summary['fitness']}`",
        f"- RMSE: `{summary['rmse']}`",
        f"- Runtime: `{summary['runtime_s']}` s",
        f"- Agent verdict: **{summary['agent_verdict']}**",
        f"- Independent GT rotation error: `{summary['gt_rotation_error_deg']}` deg",
        f"- Independent GT translation error: `{summary['gt_translation_error']}`",
        f"- Final result: **{summary['final_result']}**", "",
        "## Attempts", "",
        "| Attempt | Method | Fitness | RMSE | Runtime (s) | Verdict | Retried |",
        "|---:|---|---:|---:|---:|---|---|",
    ]
    for attempt in summary["attempts"]:
        lines.append(
            f"| {attempt['attempt']} | {attempt['method']} | {attempt['fitness']} | {attempt['rmse']} | "
            f"{attempt['runtime_s']} | {attempt['verdict']} | {attempt['retried']} |"
        )
        lines.append("")
        lines.append(f"Attempt {attempt['attempt']} parameter policy: `{json.dumps(attempt['parameter_policy'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"Attempt {attempt['attempt']} derived parameters: `{json.dumps(attempt['derived_parameters'], ensure_ascii=False, sort_keys=True)}`")
    lines += ["", "Generated deterministically from existing Run evidence. No Agent, registration, probe, or evaluator was invoked.", ""]
    return "\n".join(lines)


def _load_cloud(path: Path) -> np.ndarray:
    import open3d as o3d

    cloud = o3d.io.read_point_cloud(str(path))
    points = np.asarray(cloud.points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ValueError(f"point cloud is empty or invalid: {path}")
    return points


def _sample(points: np.ndarray, limit: int = 8000) -> np.ndarray:
    if len(points) <= limit:
        return points
    return points[np.linspace(0, len(points) - 1, limit, dtype=np.int64)]


def _render_visuals(run_dir: Path, evidence: dict[str, Any], summary: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    source = _load_cloud(evidence["source"])
    target = _load_cloud(evidence["target"])
    transform = evidence["transform"]
    aligned = source @ transform[:3, :3].T + transform[:3, 3]
    all_points = np.vstack([source, target, aligned])
    minimum, maximum = all_points.min(axis=0), all_points.max(axis=0)
    center = (minimum + maximum) / 2.0
    half = max(float(np.max(maximum - minimum)) * 0.55, 1e-9)
    source_show, target_show, aligned_show = _sample(source), _sample(target), _sample(aligned)
    visuals = run_dir / "06_VISUALS"
    visuals.mkdir(parents=True, exist_ok=True)

    support_threshold = next((
        item.get("support_distance_threshold") for item in evidence.get("probe_observations", [])
        if isinstance(item, dict) and item.get("support_distance_threshold") is not None
    ), None)
    if support_threshold is None:
        support_threshold = _value(evidence["final_observation"], "max_correspondence_distance", "icp_max_correspondence_distance", default=None)
    partial_overlap = _value(evidence.get("diagnosis"), "point_count_ratio", default=1.0)
    try:
        partial_overlap = float(partial_overlap) < 0.9
    except (TypeError, ValueError):
        partial_overlap = False

    matched_source = np.ones(len(aligned), dtype=bool)
    matched_target = np.ones(len(target), dtype=bool)
    if partial_overlap and support_threshold is not None:
        import open3d as o3d
        aligned_cloud, target_cloud = o3d.geometry.PointCloud(), o3d.geometry.PointCloud()
        aligned_cloud.points = o3d.utility.Vector3dVector(aligned)
        target_cloud.points = o3d.utility.Vector3dVector(target)
        matched_source = np.asarray(aligned_cloud.compute_point_cloud_distance(target_cloud)) <= float(support_threshold)
        matched_target = np.asarray(target_cloud.compute_point_cloud_distance(aligned_cloud)) <= float(support_threshold)

    def plot_clouds(ax: Any, source_points: np.ndarray, title: str, source_label: str) -> None:
        ax.scatter(target_show[:, 0], target_show[:, 1], target_show[:, 2], s=1.2, c=[[0.9, 0.15, 0.15]], alpha=0.55, label="target")
        ax.scatter(source_points[:, 0], source_points[:, 1], source_points[:, 2], s=1.2, c=[[0.2, 0.5, 0.95]], alpha=0.55, label=source_label)
        ax.view_init(elev=25, azim=-60)
        ax.set_xlim(center[0] - half, center[0] + half)
        ax.set_ylim(center[1] - half, center[1] + half)
        ax.set_zlim(center[2] - half, center[2] + half)
        ax.set_box_aspect((1, 1, 1))
        ax.set_title(title, fontsize=11)
        ax.legend(fontsize=8)
        ax.tick_params(labelsize=8)

    for name, points, label in (("before", source_show, "source (raw)"), ("after", aligned_show, "source (registered)")):
        fig = plt.figure(figsize=(7, 6), dpi=140)
        ax = fig.add_subplot(111, projection="3d")
        if name == "after" and partial_overlap:
            ax.scatter(target[:, 0], target[:, 1], target[:, 2], s=1.2, c=[[0.9, 0.15, 0.15]], alpha=0.55, label="target")
            ax.scatter(aligned[~matched_source, 0], aligned[~matched_source, 1], aligned[~matched_source, 2], s=1.0, c=[[0.2, 0.5, 0.95]], alpha=0.08, label="source (no nearby support)")
            ax.scatter(aligned[matched_source, 0], aligned[matched_source, 1], aligned[matched_source, 2], s=1.3, c=[[0.2, 0.5, 0.95]], alpha=0.65, label="source (supported)")
            ax.view_init(elev=25, azim=-60)
            ax.set(xlim=(center[0]-half, center[0]+half), ylim=(center[1]-half, center[1]+half), zlim=(center[2]-half, center[2]+half))
            ax.set_box_aspect((1, 1, 1)); ax.set_title("AFTER — Partial Overlap", fontsize=11); ax.legend(fontsize=8)
        else:
            plot_clouds(ax, points, name.upper(), label)
        fig.tight_layout()
        fig.savefig(visuals / f"{name}.png", dpi=140, bbox_inches="tight", metadata={"Software": "postprocess_run.py"})
        plt.close(fig)

    fig = plt.figure(figsize=(14, 6), dpi=140)
    plot_clouds(fig.add_subplot(1, 2, 1, projection="3d"), source_show, "BEFORE registration", "source (raw)")
    after_ax = fig.add_subplot(1, 2, 2, projection="3d")
    if partial_overlap:
        after_ax.scatter(target[:, 0], target[:, 1], target[:, 2], s=1.2, c=[[0.9, 0.15, 0.15]], alpha=0.55, label="target")
        after_ax.scatter(aligned[~matched_source, 0], aligned[~matched_source, 1], aligned[~matched_source, 2], s=1.0, c=[[0.2, 0.5, 0.95]], alpha=0.08, label="source (no nearby support)")
        after_ax.scatter(aligned[matched_source, 0], aligned[matched_source, 1], aligned[matched_source, 2], s=1.3, c=[[0.2, 0.5, 0.95]], alpha=0.65, label="source (supported)")
        after_ax.view_init(elev=25, azim=-60); after_ax.set_box_aspect((1, 1, 1))
        after_ax.set(xlim=(center[0]-half, center[0]+half), ylim=(center[1]-half, center[1]+half), zlim=(center[2]-half, center[2]+half))
        after_ax.set_title("AFTER registration — Partial Overlap", fontsize=11); after_ax.legend(fontsize=8)
    else:
        plot_clouds(after_ax, aligned_show, "AFTER registration", "source (registered)")
    fig.suptitle(f"{evidence['run_id']} — before / after" + (" — Partial Overlap" if partial_overlap else ""), fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(visuals / "compare.png", dpi=140, bbox_inches="tight", metadata={"Software": "postprocess_run.py"})
    plt.close(fig)

    # Detail uses only final-transform nearest-neighbour support at the recorded
    # GT-free threshold; it never consults evaluator errors or the true transform.
    detail_source = aligned[matched_source]
    detail_target = target[matched_target]
    if len(detail_source) and len(detail_target):
        detail_all = np.vstack([detail_source, detail_target])
        dmin, dmax = detail_all.min(axis=0), detail_all.max(axis=0)
        dcenter = (dmin + dmax) / 2.0
        dhalf = max(float(np.max(dmax - dmin)) * 0.55, 1e-9)
        fig = plt.figure(figsize=(7, 6), dpi=140); ax = fig.add_subplot(111, projection="3d")
        ax.scatter(detail_target[:, 0], detail_target[:, 1], detail_target[:, 2], s=2.0, c=[[0.9, 0.15, 0.15]], alpha=0.6, label="target supported region")
        ax.scatter(detail_source[:, 0], detail_source[:, 1], detail_source[:, 2], s=2.0, c=[[0.2, 0.5, 0.95]], alpha=0.6, label="registered source supported region")
        ax.view_init(elev=25, azim=-60); ax.set_box_aspect((1, 1, 1))
        ax.set(xlim=(dcenter[0]-dhalf, dcenter[0]+dhalf), ylim=(dcenter[1]-dhalf, dcenter[1]+dhalf), zlim=(dcenter[2]-dhalf, dcenter[2]+dhalf))
        threshold_label = f"{float(support_threshold):.5g}" if support_threshold is not None else "NOT_AVAILABLE"
        ax.set_title(f"Partial Overlap Detail (GT-free NN threshold={threshold_label})", fontsize=10); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(visuals / "overlap_detail.png", dpi=140, bbox_inches="tight", metadata={"Software": "postprocess_run.py"}); plt.close(fig)
    else:
        fig, ax = plt.subplots(figsize=(7, 3), dpi=140); ax.axis("off")
        ax.text(0.5, 0.5, "Overlap detail unavailable: no supported region in recorded GT-free threshold.", ha="center", va="center")
        fig.savefig(visuals / "overlap_detail.png", dpi=140, bbox_inches="tight", metadata={"Software": "postprocess_run.py"}); plt.close(fig)

    policy = json.dumps(summary["parameter_policy"], ensure_ascii=False, sort_keys=True)
    derived = json.dumps(summary["derived_parameters"], ensure_ascii=False, sort_keys=True)
    panel = [
        "AGENT / TOOL EVIDENCE (no GT)",
        f"selected_method: {summary['selected_method']}",
        *textwrap.wrap(f"parameter_policy: {policy}", 100),
        *textwrap.wrap(f"derived_parameters: {derived}", 100),
        f"fitness: {summary['fitness']}",
        f"RMSE: {summary['rmse']}",
        f"runtime_s: {summary['runtime_s']}",
        f"Agent verdict: {summary['agent_verdict']}", "",
        "INDEPENDENT GT EVALUATION (post-Agent-stop)",
        f"rotation_error_deg: {summary['gt_rotation_error_deg']}",
        f"translation_error: {summary['gt_translation_error']}",
        f"final_result: {summary['final_result']}", "",
        f"ATTEMPTS ({summary['attempt_count']}; retry={summary['retry_occurred']})",
    ]
    for attempt in summary["attempts"]:
        panel.extend(textwrap.wrap(
            f"#{attempt['attempt']} {attempt['method']} | policy={json.dumps(attempt['parameter_policy'], ensure_ascii=False, sort_keys=True)} | "
            f"fitness={attempt['fitness']} rmse={attempt['rmse']} runtime={attempt['runtime_s']} verdict={attempt['verdict']}",
            115,
        ))
    height = max(6.0, 0.34 * len(panel) + 0.8)
    fig, ax = plt.subplots(figsize=(12, height), dpi=140)
    ax.axis("off")
    ax.text(0.02, 0.98, "\n".join(panel), va="top", family="monospace", fontsize=10, transform=ax.transAxes)
    fig.suptitle(evidence["run_id"], fontsize=13)
    fig.tight_layout()
    fig.savefig(visuals / "metrics_panel.png", dpi=140, bbox_inches="tight", facecolor="white", metadata={"Software": "postprocess_run.py"})
    plt.close(fig)


def postprocess_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory does not exist: {run_dir}")
    evidence = collect_evidence(run_dir)
    summary = _summary_payload(evidence)
    _write_json(run_dir / "05_VALIDATION" / "metrics_summary.json", summary)
    index = run_dir / "00_INDEX" / "run_summary.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(_markdown(summary), encoding="utf-8")
    artifact_map = run_dir / "00_INDEX" / "ARTIFACT_MAP.md"
    artifact_map.write_text(
        "# Artifact Map\n\n"
        "Core flat JSON files at the Run root are immutable source evidence.\n\n"
        "- `00_INDEX/`: derived summaries and this map\n"
        "- `05_VALIDATION/metrics_summary.json`: derived metrics aggregation\n"
        "- `06_VISUALS/`: derived figures; overlap highlighting uses only recorded GT-free correspondence support\n",
        encoding="utf-8",
    )
    if evidence["status"] == "COMPLETE":
        _render_visuals(run_dir, evidence, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="Formal Run directory")
    args = parser.parse_args(argv)
    try:
        summary = postprocess_run(args.run_dir)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
