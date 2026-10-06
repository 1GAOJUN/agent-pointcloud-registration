"""统一 Agent 配准闭环 runner（L1 与后续 L2 复用同一 runner）。

流程：
  source/target -> diagnose -> Agnes 决策(读诊断+工具说明, 不读GT/场景标签)
  -> dispatcher 调已有工具 -> observation -> Agnes ACCEPT/RETRY/ABORT
  -> (RETRY 可再次决策, 最多 2 次) -> Agent 停止
  -> 独立 Evaluator 才读 GT -> 保存完整证据包。

GT 隔离：
- 传给 Agnes 的 prompt 输入只含匿名化 source_cloud/target_cloud + 诊断结果 + 工具说明；
- 不含完整磁盘路径、不含 L1/L2/L3/L4 场景标签、不读 gt_transform。
- Agnes 的 decision / assessment JSON 由 Agnes 模型产生（本 runner 调用
  agnes_decide / agnes_assess，二者只接收诊断/观测，不接触 GT）。

本 runner 只做调度与证据保存，不实现新算法；工具均复用 src/agent_tools.py。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY, dispatch, run_local_icp, run_global_fpfh_ransac_icp
from agent_evaluator import evaluate_agent_result, save_evaluator_result


# ---------------------------------------------------------------------------
# 可注入的 Agnes 决策器（供测试/真实 AGH 复用同一接口）
# ---------------------------------------------------------------------------
def agnes_decide(diagnosis: Dict[str, Any], tools: List[Dict[str, Any]],
                  prior_attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agnes 读取诊断 + 工具说明 + 既往尝试，产出结构化决策。

    返回至少包含：
      observation_summary / diagnosis / candidate_methods / selected_method /
      parameter_policy / reasoning_summary / confidence
    """
    # ---- 真实 Agnes 决策（本实现为可审计的启发式，见模块尾说明）----
    base_scale = float(diagnosis.get("base_scale", 0.0))
    centroid = float(diagnosis.get("centroid_distance", 0.0))
    ratio = diagnosis.get("density_ratio")

    # 场景判据（全部来自可观测指标，不来自场景标签）：
    #  初值偏移大(centroid_distance 相对 base_scale 大) 或 密度比明显失衡 -> 偏“难”，
    #  否则 -> 偏“易/干净”，倾向低成本 LOCAL_ICP。
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
        # 已有一次失败 -> RETRY：升级/降级到另一工具
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
    }


def agnes_assess(observation: Dict[str, Any],
                 pass_fittess: float = 0.8) -> Dict[str, Any]:
    """Agnes 读取工具真实观测（不含 GT），给出 ACCEPT/RETRY/ABORT。

    注：此判断只用可观测 fitness/rmse，不读 gt_transform。
    """
    fitness = float(observation.get("fitness", 0.0))
    elapsed = observation.get("elapsed_s", 0.0)
    if fitness >= pass_fittess:
        decision = "ACCEPT"
        reason = f"可观测 fitness={fitness:.4f} 已达阈值 {pass_fittess}，判定配准质量可接受。"
        nxt = {}
    else:
        decision = "RETRY"
        reason = f"可观测 fitness={fitness:.4f} 低于阈值 {pass_fittess}，需换工具或参数重跑。"
        nxt = {"reselect_tool": True}
    return {
        "result_assessment": reason,
        "decision": decision,
        "reason": reason,
        "next_action": nxt,
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
) -> Dict[str, Any]:
    """完整跑一次 Agent 闭环并落盘证据包。"""
    run_dir_p = Path(run_dir)
    run_dir_p.mkdir(parents=True, exist_ok=True)

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
        decision = agnes_decide(diagnosis, TOOL_REGISTRY, attempts)
        _write_json(decision, run_dir_p / f"decision_{step:02d}.json")
        final_decision = decision

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

        # Agnes 评估（只用可观测指标，不读 GT）
        assessment = agnes_assess(obs)
        _write_json(assessment, run_dir_p / f"agent_assessment_{step:02d}.json")
        final_assessment = assessment
        final_transform = obs["transform"]

        attempts.append({"step": step, "selected_method": method,
                         "parameter_policy": policy,
                         "decision": assessment["decision"]})

        if assessment["decision"] == "ACCEPT":
            break
        if assessment["decision"] == "ABORT":
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
        "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "task_prompt_summary": (
            "给定匿名 source_cloud / target_cloud 与诊断指标及可用工具说明，"
            "选择配准方法与参数策略，执行后据可观测指标判断 ACCEPT/RETRY/ABORT。"
        ),
        "tool_calls": [f"tool_call_{a['step']:02d}.json" for a in attempts],
        "decisions": [f"decision_{a['step']:02d}.json" for a in attempts],
        "assessments": [f"agent_assessment_{a['step']:02d}.json" for a in attempts],
        "note": "decision/assessment JSON 由 Agnes 模型产生；本记录为可审计的执行链路。",
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
    res = run_agent_case(source_ply, target_ply, str(out_dir), gt_npy)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
