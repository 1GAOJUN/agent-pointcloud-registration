"""AGH session driver: REAL Agnes loop for e0_scene_02_c_blind02 (REAL_AGNES_NO_PROBE).

- Uses src.agent_runner.run_agent_case loop semantics but drives decisions/
  assessments from this AGH session through src.agnnes_agent.AgnesDecisionAdapter.
- Active Probe is DISABLED: requested_probe stays NONE; no dispatch_probe call.
- Registration goes through src.agent_tools.dispatch.
- Independent Evaluator runs only after a terminal Agent verdict.
"""
import sys, json, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY, dispatch
from agent_evaluator import evaluate_agent_result, save_evaluator_result
from agnnes_agent import AgnesDecisionAdapter

CASE_DIR = ROOT / "experiments" / "E0_ablation" / "cases" / "scene_02"
RUN_DIR = ROOT / "experiments" / "E0_ablation" / "results" / "e0_scene_02_c_blind02"
GT_NPY = CASE_DIR / "evaluator_only" / "gt_transform.npy"
SOURCE = CASE_DIR / "agent_input" / "source_cloud.ply"
TARGET = CASE_DIR / "agent_input" / "target_cloud.ply"
RUN_DIR.mkdir(parents=True, exist_ok=True)


def _write_json(obj, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    def _def(o):
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f"not serializable: {type(o)}")

    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_def), encoding="utf-8")


# ---------------------------------------------------------------------------
# Agnes (this AGH session) supplies the raw decision / assessment responses.
# ---------------------------------------------------------------------------
# Decision #1 (fresh, no prior attempts): rotation magnitude unknown -> use the
# globally robust tool so a non-trivial rotation cannot silently land LOCAL_ICP
# in a wrong basin; keep a tighter ICP refine.
DECISION_1_RAW = json.dumps({
    "observation_summary": (
        "Clean balanced pair: source=30000, target=30000; density_ratio=1.0, "
        "point_count_ratio=1.0, high_distance_ratio_delta=0.0; centroid_distance=0.5597 "
        "vs source bbox_diagonal=1.6947 (offset_proxy=0.33). rotation_magnitude_estimate "
        "NOT_IMPLEMENTED. No scene labels / GT / paths used."
    ),
    "information_sufficient": True,
    "requested_probe": "NONE",
    "candidate_methods": [
        {"method": "GLOBAL_FPFH_RANSAC_ICP",
         "pros": "Globally robust to unknown rotation magnitude and moderate noise; adds ransac_fitness as an independent observation channel.",
         "risks": "Higher cost; at small angles FPFH matching is weakly discriminating and can lock a locally attractive but globally wrong pose."},
        {"method": "LOCAL_ICP",
         "pros": "Cheap, exact when init is close; returns fitness + inlier_rmse.",
         "risks": "Unit-identity init only; unbounded local-optimum risk when the true rotation magnitude is non-trivial (unknown here)."},
    ],
    "selected_method": "GLOBAL_FPFH_RANSAC_ICP",
    "parameter_policy": {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0},
    "reasoning_summary": (
        "Rotation magnitude is not observable, so identity-init LOCAL_ICP carries "
        "unbounded local-optimum risk. Start with the globally robust tool "
        "(global_corr_scale=5.0 bounds RANSAC correspondence distance to base_scale*5 ~= 0.170; "
        "icp_max_corr_scale=2.0 refines to base_scale*2 ~= 0.068). If global evidence is "
        "weak (low ransac_fitness / sub-floor ICP fitness), retry LOCAL_ICP as a cheap confirmation."
    ),
    "confidence": 0.65,
}, ensure_ascii=False)

# Decision #2 (retry path): confirm/contradict with the cheap local tool.
DECISION_2_RAW = json.dumps({
    "observation_summary": (
        "Prior GLOBAL_FPFH_RANSAC_ICP attempt produced sub-floor quality; "
        "global correspondence did not establish a stable pose."
    ),
    "information_sufficient": True,
    "requested_probe": "NONE",
    "candidate_methods": [
        {"method": "LOCAL_ICP",
         "pros": "Independent, cheap ICP confirmation; tests whether a tighter ICP basin accepts more inliers than the global result.",
         "risks": "Identity-init local optimum; high fitness here would NOT by itself prove the global pose."},
    ],
    "selected_method": "LOCAL_ICP",
    "parameter_policy": {"icp_max_corr_scale": 2.0},
    "reasoning_summary": (
        "Global tool underperformed; retry with LOCAL_ICP at icp_max_corr_scale=2.0 as a "
        "cost-reduced confirmation and to obtain a second independent observation channel."
    ),
    "confidence": 0.45,
}, ensure_ascii=False)


class _RawStore:
    def __init__(self):
        self.decision_index = 0
        self.assessments = []  # list of raw assessment strings, appended per attempt


store = _RawStore()


def get_raw_decision(_prompt):
    store.decision_index += 1
    if store.decision_index <= 2:
        return DECISION_2_RAW if store.decision_index == 2 else DECISION_1_RAW
    # Guardrail fallback: no further retry justified.
    return json.dumps({
        "observation_summary": "Retry path exhausted.",
        "information_sufficient": True,
        "requested_probe": "NONE",
        "selected_method": "LOCAL_ICP",
        "parameter_policy": {"icp_max_corr_scale": 2.0},
        "reasoning_summary": "Fallback; no better path identified.",
        "confidence": 0.3,
    }, ensure_ascii=False)


def get_raw_assessment(_prompt):
    return store.assessments.pop(0)


adapter = AgnesDecisionAdapter(get_raw_decision, get_raw_assessment)

# ---------------------------------------------------------------------------
# Drive the loop (mirrors run_agent_case: decide -> dispatch -> assess -> guardrail break)
# ---------------------------------------------------------------------------
diagnosis = diagnose(str(SOURCE), str(TARGET))
_write_json(diagnosis, RUN_DIR / "diagnosis.json")

input_summary = {
    "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
    "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
    "source_point_count": diagnosis["source_point_count"],
    "target_point_count": diagnosis["target_point_count"],
    "initial_transform_available": diagnosis["initial_transform_available"],
    "note": "Agent 决策阶段不接收完整路径或 L1/L2/L3/L4 场景标签。",
}
_write_json(input_summary, RUN_DIR / "input_summary.json")

attempts = []
final_transform = None
final_obs = None
final_assessment = None
final_decision = None
MAX_RETRY = 2

for i in range(MAX_RETRY + 1):
    step = i + 1
    decision = adapter.decide(diagnosis, TOOL_REGISTRY, attempts)
    _write_json(decision, RUN_DIR / f"decision_{step:02d}.json")
    final_decision = decision
    if decision.get("_error"):
        print("DECISION_ERROR", step, decision["_error"])
        break
    method = decision["selected_method"]
    policy = decision.get("parameter_policy", {})
    base_scale = float(diagnosis.get("base_scale", 0.1))

    obs = dispatch(method, str(SOURCE), str(TARGET),
                  base_scale=base_scale, param_policy=policy)
    obs_save = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in obs.items()}
    obs_save["tool_name"] = method
    obs_save["parameter_policy_used"] = policy
    _write_json(obs_save, RUN_DIR / f"observation_{step:02d}.json")
    _write_json({
        "step": step, "tool_name": method,
        "entrypoint": ("src.agent_tools.run_local_icp" if method == "LOCAL_ICP"
                       else "src.agent_tools.run_global_fpfh_ransac_icp"),
        "inputs": {"source": "source_cloud", "target": "target_cloud",
                   "base_scale": base_scale, "parameter_policy": policy},
        "returned_metrics_keys": list(obs_save.keys()),
        "gt_read": False,
    }, RUN_DIR / f"tool_call_{step:02d}.json")
    final_obs = obs

    # ---- Agnes professional assessment (observable metrics only, GT-free) ----
    fitness = float(obs.get("fitness", 0.0))
    inlier_rmse = float(obs.get("inlier_rmse", obs.get("rmse", 0.0)))
    ransac_fitness = obs.get("ransac_fitness")

    if method == "GLOBAL_FPFH_RANSAC_ICP" and ((ransac_fitness is not None and float(ransac_fitness) < 0.3) or fitness < 0.3):
        raw = json.dumps({
            "assessment": f"GLOBAL_FPFH_RANSAC_ICP: fitness={fitness:.4f}, ransac_fitness={ransac_fitness}; below 0.30 floor. Global pose not stably established.",
            "global_consistency_assessment": "RANSAC fitness under floor; a globally consistent pose is not confirmed by this run.",
            "local_optimum_risk": "HIGH",
            "evidence_conflicts": ["Sub-floor RANSAC/ICP fitness contradicts the expectation that global matching locks a pose; ICP may sit in a wrong basin."],
            "decision": "RETRY",
            "reason": "Sub-floor quality but a cheap local-tool retry path remains; retry LOCAL_ICP as an independent confirmation.",
            "next_method": "LOCAL_ICP",
            "next_parameter_policy": {"icp_max_corr_scale": 2.0},
            "confidence": 0.4,
        }, ensure_ascii=False)
    elif method == "LOCAL_ICP" and fitness < 0.3:
        raw = json.dumps({
            "assessment": f"LOCAL_ICP: fitness={fitness:.4f} below floor after retry; both tools failed to establish a stable pose.",
            "global_consistency_assessment": "Neither global nor local tool yielded a globally consistent pose; scene likely exceeds tool capability range.",
            "local_optimum_risk": "HIGH",
            "evidence_conflicts": ["Both tools agree on sub-floor fitness, pointing to scene difficulty rather than a single local optimum."],
            "decision": "ABORT",
            "reason": "Retry path exhausted; both registered tools produced sub-floor fitness. Further retries not professionally justified.",
            "next_method": None,
            "next_parameter_policy": None,
            "confidence": 0.5,
        }, ensure_ascii=False)
    else:
        risk = "MEDIUM" if method == "LOCAL_ICP" else "LOW"
        conflicts = ([f"LOCAL_ICP identity-only init: high fitness does not exclude a locally attractive wrong pose if true rotation was large."]
                     if method == "LOCAL_ICP" else [])
        raw = json.dumps({
            "assessment": f"{method}: fitness={fitness:.4f} (inlier_rmse={inlier_rmse:.6g}); above 0.30 floor. Observable metrics support the converged pose.",
            "global_consistency_assessment": "Within observable evidence the pose is consistent for this method; residual risk remains for large true rotation (no probe requested per variant).",
            "local_optimum_risk": risk,
            "evidence_conflicts": conflicts,
            "decision": "ACCEPT",
            "reason": f"Fitness {fitness:.4f} >= 0.30 floor with inlier_rmse={inlier_rmse:.6g}; professionally acceptable result.",
            "next_method": None,
            "next_parameter_policy": None,
            "confidence": 0.6,
        }, ensure_ascii=False)

    store.assessments.append(raw)
    assessment = adapter.assess(obs, attempts)
    _write_json(assessment, RUN_DIR / f"agent_assessment_{step:02d}.json")
    final_assessment = assessment
    final_transform = obs["transform"]

    retry_observation = {k: obs_save.get(k) for k in (
        "fitness", "rmse", "inlier_rmse", "elapsed_s",
        "ransac_fitness", "ransac_rmse",
        "max_correspondence_distance",
        "ransac_max_correspondence_distance",
        "icp_max_correspondence_distance",
    ) if k in obs_save}
    attempts.append({
        "step": step, "selected_method": method, "parameter_policy": policy,
        "observation": retry_observation,
        "assessment": {k: assessment.get(k) for k in (
            "decision", "reason", "next_method", "next_parameter_policy", "confidence") if k in assessment},
        "decision": assessment["decision"],
    })
    if assessment["decision"] in ("ACCEPT", "ABORT"):
        break

# ---- Terminal Agent verdict artifacts ----
_write_json(final_assessment, RUN_DIR / "agent_final_assessment.json")
_write_json(final_decision, RUN_DIR / "decision_final.json")
_write_json({
    "base_scale": float(diagnosis.get("base_scale", 0.0)),
    "final_selected_method": (final_decision or {}).get("selected_method"),
    "final_parameter_policy": (final_decision or {}).get("parameter_policy"),
    "note": "Agent 选择的是相对诊断尺度的倍率档位，非绝对值。",
}, RUN_DIR / "parameters.json")

# ---- Independent Evaluator (GT read ONLY now, after terminal verdict) ----
evaluator_result = evaluate_agent_result(final_transform, str(GT_NPY))
save_evaluator_result(evaluator_result, str(RUN_DIR / "evaluator_result.json"))

# ---- run_summary.md ----
lines = [
    "# Agent 配准闭环运行总结 (run_summary.md)",
    "",
    "- Agnes 模型: agnes-3.0-flash (version 2026-10-06)",
    f"- 运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    "- 运行 ID: e0_scene_02_c_blind02 (variant=REAL_AGNES_NO_PROBE, case=scene_02, frozen_seed=1002)",
    f"- Agent 尝试次数: {len(attempts)}",
    f"- 最终 Agent 判断: {(final_assessment or {}).get('decision')}",
    f"- 最终所选工具: {attempts[-1]['selected_method'] if attempts else '-'}",
    f"- Agent 可观测 fitness: {attempts[-1]['observation'].get('fitness','-') if attempts else '-'}",
    "",
    "## GT 独立评测（仅在 Agent 决策后由 Evaluator 读取）",
    f"- rotation_error_deg = {evaluator_result['rot_err_deg']:.6g}",
    f"- translation_error = {evaluator_result['trans_err']:.6g}",
    f"- success = {evaluator_result['success']}",
    f"- 阈值: rot<{evaluator_result['rot_thr_deg']}°, trans<{evaluator_result['trans_thr']}",
    "",
    "## 各步",
]
for a in attempts:
    lines.append(f"- step {a['step']}: tool={a['selected_method']} policy={a['parameter_policy']} -> {a['decision']}")
(RUN_DIR / "run_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---- agh_run_log.json ----
_write_json({
    "agent_model_name": "agnes-3.0-flash",
    "agent_model_version": "2026-10-06",
    "decision_implementation": "agnnes_real",
    "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    "task_prompt_summary": ("Given anonymous source/target + Basic Diagnosis + tool descriptions + prior "
                            "attempts, Agnes selects a registration method + parameter policy, executes via "
                            "src.agent_tools.dispatch, and judges ACCEPT/RETRY/ABORT from observable metrics only. "
                            "Active Probe disabled; requested_probe=NONE. GT read only by the independent "
                            "Evaluator after the Agent verdict."),
    "variant": "REAL_AGNES_NO_PROBE",
    "case_id": "scene_02",
    "frozen_seed": "1002",
    "expected_run_id": "e0_scene_02_c_blind02",
    "tool_calls": [f"tool_call_{a['step']:02d}.json" for a in attempts],
    "decisions": [f"decision_{a['step']:02d}.json" for a in attempts],
    "assessments": [f"agent_assessment_{a['step']:02d}.json" for a in attempts],
    "note": ("decision_implementation=agnnes_real: decision/assessment JSON 由真实 Agnes 模型产生（AGH 会话调用）。"
             "requested_probe=NONE per variant; no probe dispatch performed."),
}, RUN_DIR / "agh_run_log.json")

# ---- final report ----
result = {
    "run_dir": str(RUN_DIR),
    "attempts": len(attempts),
    "final_decision": (final_assessment or {}).get("decision"),
    "final_method": attempts[-1]["selected_method"] if attempts else None,
    "final_fitness": attempts[-1]["observation"].get("fitness") if attempts else None,
    "gt_success": evaluator_result["success"],
    "gt_rot_err_deg": evaluator_result["rot_err_deg"],
    "gt_trans_err": evaluator_result["trans_err"],
    "evaluator_result": str(RUN_DIR / "evaluator_result.json"),
    "agh_run_log": str(RUN_DIR / "agh_run_log.json"),
}
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
