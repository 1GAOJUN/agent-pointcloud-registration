"""Agent 配准闭环 runner（L1 与后续 L2 复用同一 runner）。

B2A 架构说明（Phase B2A — Real Agnes Decision Integration）：

决策层分离：
- heuristic_decide / heuristic_assess：确定性 Python 启发式，保留为 baseline 对照
- Agnes 决策/评估：由 AGH 外层编排机制调用（subagent_fork 或等价），
  通过注入 agnes_decide_fn / agnes_assess_fn 接入，Python 不再替代 Agent 决定算法/参数

GT 隔离：
- 传给 Agnes 的输入只含匿名化 diagnosis + 工具说明 + 既往 attempts；
- 不含磁盘路径、场景标签、gt_transform。
- Evaluator 只在 Agent 停止后读取 GT，时序不变。

本 runner 只做调度与证据保存，不实现新算法；工具均复用 src/agent_tools.py。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

import numpy as np

from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY, dispatch, run_local_icp, run_global_fpfh_ransac_icp
from agent_probes import dispatch_probe
from agent_evaluator import evaluate_agent_result, save_evaluator_result
from agnnes_agent import MAX_PROBES_PER_RUN


class AgnesDecideFn(Protocol):
    """真实 Agnes 决策器：读 diagnosis + tools + prior_attempts，输出 structured decision。"""
    def __call__(self, diagnosis: Dict[str, Any],
                 tools: List[Dict[str, Any]],
                 prior_attempts: List[Dict[str, Any]]) -> Dict[str, Any]: ...


class AgnesAssessFn(Protocol):
    """真实 Agnes 评估器：读 observation + prior_attempts，输出 ACCEPT/RETRY/ABORT。"""
    def __call__(self, observation: Dict[str, Any],
                 prior_attempts: List[Dict[str, Any]]) -> Dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Heuristic Baseline（Phase A/B0 保留，@deprecated — 不得作为 Agnes 决策证据）
# B1 审计确认：以下函数是确定性 Python 分支，非 LLM 调用。
# 仅供 baseline 对照使用；主路径使用 agnes_decide_fn / agnes_assess_fn 注入。
# ---------------------------------------------------------------------------
def heuristic_decide(diagnosis: Dict[str, Any], tools: List[Dict[str, Any]],
                     prior_attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """确定性 Python heuristic：easy/hard 分支，算法/参数均为字面量，无 LLM 调用。

    @deprecated — B2A 之后仅保留为 baseline 对照，不得用于正式 Agnes 证明。
    返回字段与真实 Agnes 路径 schema 对齐（便于对比测试）。
    """
    base_scale = float(diagnosis.get("base_scale", 0.0))
    centroid = float(diagnosis.get("centroid_distance", 0.0))
    ratio = diagnosis.get("density_ratio")
    offset_proxy = centroid / max(base_scale, 1e-9)
    easy = offset_proxy < 3.0 and (ratio is None or 0.5 < ratio < 2.0)

    if not prior_attempts and easy:
        selected = "LOCAL_ICP"
        policy = {"icp_max_corr_scale": 2.0}
        reasoning = "初值偏移小、密度比均衡，判定为小角度干净场景，优先低成本 ICP。"
        candidate = ["LOCAL_ICP", "GLOBAL_FPFH_RANSAC_ICP"]
        conf = 0.7
    elif not prior_attempts:
        selected = "GLOBAL_FPFH_RANSAC_ICP"
        policy = {"global_corr_scale": 5.0, "icp_max_corr_scale": 2.0}
        reasoning = "初值偏移大或密度比失衡，判定为较难场景，直接用全局配准兜底。"
        candidate = ["GLOBAL_FPFH_RANSAC_ICP", "LOCAL_ICP"]
        conf = 0.6
    else:
        last_fail = [a for a in prior_attempts if a.get("decision") == "RETRY"]
        used = {a.get("selected_method") for a in last_fail}
        selected = "LOCAL_ICP" if "GLOBAL_FPFH_RANSAC_ICP" in used else "GLOBAL_FPFH_RANSAC_ICP"
        policy = ({"icp_max_corr_scale": 1.5} if selected == "LOCAL_ICP"
                  else {"global_corr_scale": 4.0, "icp_max_corr_scale": 1.5})
        reasoning = "首次工具未达标，RETRY 切换至另一候选工具并收紧对应距离阈值倍率。"
        candidate = ["LOCAL_ICP", "GLOBAL_FPFH_RANSAC_ICP"]
        conf = 0.45

    return {
        "observation_summary": (
            f"source={diagnosis.get('source_point_count')}点, "
            f"target={diagnosis.get('target_point_count')}点, "
            f"centroid_distance={centroid:.4f}, density_ratio={ratio}, "
            f"base_scale={base_scale:.5f}"
        ),
        "diagnosis": "基于可观测指标判断场景难度，不依赖场景标签/真值",
        "candidate_methods": candidate,
        "selected_method": selected,
        "parameter_policy": policy,
        "reasoning_summary": reasoning,
        "confidence": conf,
        "_implementation": "heuristic_baseline",
    }


def heuristic_assess(observation: Dict[str, Any],
                     prior_attempts: List[Dict[str, Any]] = None,
                     pass_fittess: float = 0.8) -> Dict[str, Any]:
    """确定性 Python threshold：fitness >= 0.8 → ACCEPT，else RETRY。无 ABORT 路径。

    @deprecated — B2A 之后仅保留为 baseline 对照，不得用于正式 Agnes 证明。
    """
    fitness = float(observation.get("fitness", 0.0))
    if fitness >= pass_fittess:
        decision = "ACCEPT"
        reason = f"可观测 fitness={fitness:.4f} 已达阈值 {pass_fittess}，判定配准质量可接受。"
        nxt: Dict[str, Any] = {}
    else:
        decision = "RETRY"
        reason = f"可观测 fitness={fitness:.4f} 低于阈值 {pass_fittess}，需换工具或参数重跑。"
        nxt = {"reselect_tool": True}
    return {
        "result_assessment": reason,
        "decision": decision,
        "reason": reason,
        "next_action": nxt,
        "_implementation": "heuristic_baseline",
    }


# ---------------------------------------------------------------------------
# 证据包写入
# ---------------------------------------------------------------------------
def _write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _def(o: Any) -> Any:
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f"not serializable: {type(o)}")

    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_def), encoding="utf-8")


def run_agent_case(
    source_ply: str,
    target_ply: str,
    run_dir: str,
    gt_npy: str,
    max_retry: int = 2,
    agent_model_name: str = "agnes-3.0-flash",
    agent_model_version: str = "2026-10-06",
    # B2A：Agnes 决策器注入（None → 使用 heuristic baseline）
    agnes_decide_fn: Optional[AgnesDecideFn] = None,
    agnes_assess_fn: Optional[AgnesAssessFn] = None,
    variant: str = "REAL_AGNES_NO_PROBE",
    probe_state: Optional[Dict[str, List[Any]]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """完整跑一次 Agent 闭环并落盘证据包。

    B2A 架构：
    - 若 agnes_decide_fn / agnes_assess_fn 已注入 → 走真实 Agnes 路径
    - 若为 None → 走 heuristic baseline（@deprecated，仅用于对照）
    """
    if variant not in ("REAL_AGNES_NO_PROBE", "REAL_AGNES_ACTIVE_PROBE"):
        raise ValueError(f"unsupported E0 variant: {variant}")

    # 选路
    _decide = agnes_decide_fn or heuristic_decide
    _assess = agnes_assess_fn or (lambda obs, priors=None: heuristic_assess(obs, priors))
    _impl = "agnnes_real" if (agnes_decide_fn and agnes_assess_fn) else "heuristic_baseline"
    run_dir_p = Path(run_dir)
    run_dir_p.mkdir(parents=True, exist_ok=True)
    if probe_state is None:
        probe_state = {"probes_already_run": [], "probe_observations": []}
    probes_already_run = probe_state.setdefault("probes_already_run", [])
    probe_observations = probe_state.setdefault("probe_observations", [])
    decision_files: List[str] = []
    probe_files: List[str] = []
    decision_round = 0

    # 1) 诊断（GT-free）
    diagnosis = diagnose(source_ply, target_ply)
    _write_json(diagnosis, run_dir_p / "diagnosis.json")

    # 输入摘要：只暴露匿名化信息，不含磁盘路径/场景标签
    input_summary = {
        "source_cloud": "source_cloud (3D point cloud, path withheld from Agent)",
        "target_cloud": "target_cloud (3D point cloud, path withheld from Agent)",
        "source_point_count": diagnosis["source_point_count"],
        "target_point_count": diagnosis["target_point_count"],
        "initial_transform_available": diagnosis["initial_transform_available"],
        "note": "Agent 决策阶段不接收完整路径或 L1/L2/L3/L4 场景标签。",
    }
    _write_json(input_summary, run_dir_p / "input_summary.json")

    attempts: List[Dict[str, Any]] = []
    final_transform = None
    final_obs: Optional[Dict[str, Any]] = None
    final_assessment: Optional[Dict[str, Any]] = None
    final_decision: Optional[Dict[str, Any]] = None

    # 2) 决策-执行-评估 循环（最多 max_retry 次 RETRY）
    for i in range(max_retry + 1):
        step = i + 1
        while True:
            decision_round += 1
            decision = _decide(diagnosis, TOOL_REGISTRY, attempts)
            if not isinstance(decision, dict):
                raise RuntimeError(
                    f"invalid Agnes Decision schema: expected object, got {type(decision).__name__}")
            decision_name = f"decision_{decision_round:02d}.json"
            _write_json(decision, run_dir_p / decision_name)
            decision_files.append(decision_name)
            final_decision = decision

            if decision.get("_error"):
                raise RuntimeError(f"invalid Agnes decision: {decision['_error']}")

            information_sufficient = decision.get("information_sufficient", True)
            requested_probe = decision.get("requested_probe", "NONE")
            if information_sufficient:
                if requested_probe != "NONE":
                    raise RuntimeError(
                        "invalid Agnes decision: information_sufficient=true requires requested_probe=NONE")
                break

            if variant == "REAL_AGNES_NO_PROBE":
                raise RuntimeError(
                    f"probe '{requested_probe}' requested but disabled by REAL_AGNES_NO_PROBE")
            if len(probes_already_run) >= MAX_PROBES_PER_RUN:
                raise RuntimeError(
                    f"probe quota exhausted ({len(probes_already_run)}/{MAX_PROBES_PER_RUN})")
            if requested_probe in probes_already_run:
                raise RuntimeError(f"duplicate probe request: {requested_probe}")

            probe_obs = dispatch_probe(
                requested_probe,
                source_ply,
                target_ply,
                base_scale=float(diagnosis.get("base_scale", 0.1)),
            )
            probe_obs_save = {
                k: (v.tolist() if isinstance(v, np.ndarray) else v)
                for k, v in probe_obs.items()
            }
            probe_obs_save["probe_name"] = requested_probe
            probe_obs_save["gt_read"] = False
            probe_index = len(probes_already_run) + 1
            probe_name = f"probe_{probe_index:02d}_{requested_probe}.json"
            _write_json(probe_obs_save, run_dir_p / probe_name)
            probe_files.append(probe_name)
            probes_already_run.append(requested_probe)
            probe_observations.append(probe_obs_save)

        method = decision["selected_method"]
        policy = decision.get("parameter_policy", {})
        base_scale = float(diagnosis.get("base_scale", 0.1))

        # 工具调用（可观测指标，GT-free）
        if method == "LOCAL_ICP":
            obs = run_local_icp(source_ply, target_ply,
                                icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
                                base_scale=base_scale)
        elif method == "GLOBAL_FPFH_RANSAC_ICP":
            obs = run_global_fpfh_ransac_icp(
                source_ply, target_ply,
                global_corr_scale=policy.get("global_corr_scale", 5.0),
                icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
                base_scale=base_scale)
        else:
            raise ValueError(f"Agent 选择了不可用工具: {method}")

        # 存可观测结果（transform 用矩阵存，方便后续 evaluator 读回）
        obs_save = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in obs.items()}
        obs_save["tool_name"] = method
        obs_save["parameter_policy_used"] = policy
        _write_json(obs_save, run_dir_p / f"observation_{step:02d}.json")
        # 工具调用记录
        tool_call = {
            "step": step,
            "tool_name": method,
            "entrypoint": ("src.agent_tools.run_local_icp" if method == "LOCAL_ICP"
                           else "src.agent_tools.run_global_fpfh_ransac_icp"),
            "inputs": {"source": "source_cloud", "target": "target_cloud",
                        "base_scale": base_scale, "parameter_policy": policy},
            "returned_metrics_keys": list(obs_save.keys()),
            "gt_read": False,
        }
        _write_json(tool_call, run_dir_p / f"tool_call_{step:02d}.json")
        final_obs = obs

        # 评估（Agnes 路径 或 heuristic baseline）
        assessment = _assess(obs, attempts) if agnes_assess_fn else heuristic_assess(obs, attempts)
        if not isinstance(assessment, dict):
            raise RuntimeError(
                f"invalid Agnes Assessment schema: expected object, got {type(assessment).__name__}")
        _write_json(assessment, run_dir_p / f"agent_assessment_{step:02d}.json")
        if assessment.get("_error"):
            raise RuntimeError(f"invalid Agnes Assessment schema: {assessment['_error']}")
        verdict = assessment.get("decision")
        if verdict not in ("ACCEPT", "RETRY", "ABORT"):
            raise RuntimeError(
                "invalid Agnes Assessment schema: required decision must be "
                f"ACCEPT/RETRY/ABORT, got {verdict!r}")
        final_assessment = assessment
        final_transform = obs["transform"]

        # Feed only compact GT-free quality observations back into the next Agnes decision.
        # This makes RETRY actionable without turning Python into a method/parameter policy.
        retry_observation = {
            k: obs_save.get(k) for k in (
                "fitness", "rmse", "inlier_rmse", "elapsed_s",
                "ransac_fitness", "ransac_rmse",
                "max_correspondence_distance",
                "ransac_max_correspondence_distance",
                "icp_max_correspondence_distance",
            ) if k in obs_save
        }
        attempts.append({
            "step": step,
            "selected_method": method,
            "parameter_policy": policy,
            "observation": retry_observation,
            "assessment": {
                k: assessment.get(k) for k in (
                    "decision", "reason", "next_method",
                    "next_parameter_policy", "confidence",
                ) if k in assessment
            },
            "decision": verdict,
        })

        if verdict == "ACCEPT":
            break
        if verdict == "ABORT":
            break
        # RETRY：继续循环

    # 3) Agent 最终评估（写主文件）
    _write_json(final_assessment, run_dir_p / "agent_final_assessment.json")
    _write_json(final_decision, run_dir_p / "decision_final.json")

    # 4) 参数快照
    parameters = {
        "base_scale": float(diagnosis.get("base_scale", 0.0)),
        "final_selected_method": (final_decision or {}).get("selected_method"),
        "final_parameter_policy": (final_decision or {}).get("parameter_policy"),
        "note": "Agent 选择的是相对诊断尺度的倍率档位，非绝对值。",
    }
    _write_json(parameters, run_dir_p / "parameters.json")

    # 5) 独立 Evaluator：只有 Agent 已 ACCEPT/ABORT（或循环结束）后才读 GT
    evaluator_result = evaluate_agent_result(final_transform, gt_npy)
    save_evaluator_result(evaluator_result, str(run_dir_p / "evaluator_result.json"))

    # 6) run_summary.md
    _write_run_summary(run_dir_p, input_summary, diagnosis, attempts,
                       final_assessment, evaluator_result, agent_model_name,
                       agent_model_version)

    # 7) AGH / Agnes 运行记录
    agh_log = {
        "agent_model_name": agent_model_name,
        "agent_model_version": agent_model_version,
        "decision_implementation": _impl,
        "variant": variant,
        "run_id": run_id or run_dir_p.name,
        "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "task_prompt_summary": (
            "给定匿名 source_cloud / target_cloud 与诊断指标及可用工具说明，"
            "选择配准方法与参数策略，执行后据可观测指标判断 ACCEPT/RETRY/ABORT。"
        ),
        "tool_calls": [f"tool_call_{a['step']:02d}.json" for a in attempts],
        "decisions": decision_files,
        "assessments": [f"agent_assessment_{a['step']:02d}.json" for a in attempts],
        "probes_executed": list(probes_already_run),
        "probe_files": probe_files,
        "note": (
            "decision_implementation=agnnes_real: decision/assessment JSON 由真实 Agnes 模型产生（AGH 会话调用）。\n"
            "decision_implementation=heuristic_baseline: @deprecated，确定性 Python 分支，非 LLM 调用。"
        ),
    }
    _write_json(agh_log, run_dir_p / "agh_run_log.json")

    return {
        "run_dir": str(run_dir_p),
        "attempts": len(attempts),
        "final_decision": (final_assessment or {}).get("decision"),
        "gt_success": evaluator_result["success"],
        "gt_rot_err_deg": evaluator_result["rot_err_deg"],
        "gt_trans_err": evaluator_result["trans_err"],
        "evaluator_result": str(run_dir_p / "evaluator_result.json"),
        "agh_run_log": str(run_dir_p / "agh_run_log.json"),
        "probe_count": len(probes_already_run),
    }


def _write_run_summary(run_dir: Path, input_summary, diagnosis, attempts,
                       final_assessment, evaluator_result, model_name, model_ver) -> None:
    lines = []
    lines.append("# Agent 配准闭环运行总结 (run_summary.md)")
    lines.append("")
    lines.append(f"- Agnes 模型: {model_name} (version {model_ver})")
    lines.append(f"- 运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- Agent 尝试次数: {len(attempts)}")
    lines.append(f"- 最终 Agent 判断: {(final_assessment or {}).get('decision')}")
    lines.append(f"- 最终所选工具: {attempts[-1]['selected_method'] if attempts else '-'}")
    lines.append(f"- Agent 可观测 fitness: {attempts[-1].get('fitness', '-')}")
    lines.append("")
    lines.append("## GT 独立评测（仅在 Agent 决策后由 Evaluator 读取）")
    lines.append(f"- rotation_error_deg = {evaluator_result['rot_err_deg']:.6g}")
    lines.append(f"- translation_error = {evaluator_result['trans_err']:.6g}")
    lines.append(f"- success = {evaluator_result['success']}")
    lines.append(f"- 阈值: rot<{evaluator_result['rot_thr_deg']}°, trans<{evaluator_result['trans_thr']}")
    lines.append("")
    lines.append("## 各步")
    for a in attempts:
        lines.append(f"- step {a['step']}: tool={a['selected_method']} "
                     f"policy={a['parameter_policy']} -> {a['decision']}")
    (run_dir / "run_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    import sys
    # 用法: python src/agent_runner.py <run_id> [source_ply target_ply gt_npy]
    root = Path(__file__).resolve().parents[1]
    run_id = sys.argv[1] if len(sys.argv) > 1 else "l1_seed_101"
    if len(sys.argv) > 3:
        source_ply, target_ply, gt_npy = sys.argv[2], sys.argv[3], sys.argv[4]
    else:
        # 默认 L1 正式 case（内部已知路径；不给 Agent 的路径）
        case = root / "outputs" / "ICP" / "L1" / "L1" / "seed_101"
        source_ply = str(case / "source.ply")
        target_ply = str(case / "target.ply")
        gt_npy = str(case / "gt_transform.npy")
    out_dir = root / "outputs" / "agent_runs" / run_id
    # B2A：CLI 直接运行使用 heuristic baseline（真实 Agnes 路径通过 AGH 会话注入）
    res = run_agent_case(source_ply, target_ply, str(out_dir), gt_npy)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
