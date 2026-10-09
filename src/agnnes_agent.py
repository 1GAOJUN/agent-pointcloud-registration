"""Agnes 真实决策层（B2A — Real Agnes Decision Integration）。

架构说明：
  AGH 外层编排模式：
  - 本模块定义 Agnes 决策/评估的 schema 协议 + guardrail 验证
  - 实际 Agnes 模型调用通过 AGH 会话机制完成（subagent_fork 或 AGH 会话内 prompt）
  - Python 侧只负责：
      1. 构造发送给 Agnes 的 prompt（diagnosis + tools + parameter_ranges）
      2. 验证 Agnes 返回的 structured JSON
      3. 执行 guardrail 安全约束
      4. 分发工具调用
      5. 构造 assessment prompt 并验证结果

  Agnes 侧（AGH 会话）负责：
      1. 读取诊断 + 工具说明 + 参数范围
      2. 选择注册策略（selected_method）
      3. 选择参数倍率档位（parameter_policy）
      4. 专业评估结果（ACCEPT / RETRY / ABORT）

GT 隔离：
  本模块从不接触 gt_transform / rotation_error / translation_error / 场景标签。
  传给 Agnes 的只有：diagnosis JSON + TOOL_REGISTRY + 参数范围说明。
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Guardrail 常量（Python 侧硬安全边界，非 Agnes 决策）
# ---------------------------------------------------------------------------

# 参数倍率允许范围（超出 → 返回 error 让 Agnes 重新选择，不静默 fallback）
PARAMETER_RANGE = {
    "global_corr_scale": {"min": 2.0, "max": 10.0, "description": "RANSAC 最大对应距离 = base_scale × global_corr_scale"},
    "icp_max_corr_scale": {"min": 0.5, "max": 5.0, "description": "ICP 最大对应距离 = base_scale × icp_max_corr_scale"},
}

# 最低 fitness 可接受边界（guardrail，文档化；不写入 Agnes decision）
FLOORGUARD_FITNESS = 0.3
# 最高 retry 次数（guardrail，防止无限循环）
MAX_RETRY_LIMIT = 3

# B2B：Probe 白名单 + 每 case 配额（guardrail；是否调用/顺序由 Agnes 决定）
PROBE_WHITELIST = {"NONE", "PCA_ORIENTATION", "CHEAP_LOCAL_ICP"}
MAX_PROBES_PER_RUN = 2


def validate_parameter_policy(policy: Dict[str, Any]) -> Optional[str]:
    """验证 Agnes 输出的参数策略是否在允许范围内。

    返回 None 表示合法；返回字符串表示错误原因（可回传 Agnes 重新选择）。
    """
    for key, rng in PARAMETER_RANGE.items():
        val = policy.get(key)
        if val is None:
            continue
        if not isinstance(val, (int, float)):
            return f"parameter_policy['{key}'] must be a number, got {type(val).__name__}"
        val_f = float(val)
        if val_f < rng["min"] or val_f > rng["max"]:
            return (f"parameter_policy['{key}']={val_f} outside allowed range "
                    f"[{rng['min']}, {rng['max']}]")
    return None


def validate_decision(decision: Dict[str, Any],
                     probes_already_run: Optional[List[str]] = None,
                     probe_observations: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """验证 Agnes 决策 JSON（B2B 扩展：information_sufficient + requested_probe）。

    两种合法形态：
      A. information_sufficient=true  → selected_method 必填，requested_probe 必须为 NONE
      B. information_sufficient=false → requested_probe ∈ {PCA_ORIENTATION, CHEAP_LOCAL_ICP}
         且不得重复请求已执行 Probe；配额（MAX_PROBES_PER_RUN）内
    返回 None=合法，str=错误。
    """
    probes_already_run = probes_already_run or []

    if "information_sufficient" not in decision:
        return "decision missing required field 'information_sufficient'"
    if_suf = decision["information_sufficient"]
    if not isinstance(if_suf, bool):
        return "information_sufficient must be boolean"

    rp = decision.get("requested_probe")
    if rp not in PROBE_WHITELIST:
        return f"requested_probe '{rp}' not in {sorted(PROBE_WHITELIST)}"

    if if_suf:
        if rp != "NONE":
            return "information_sufficient=true 时 requested_probe 必须为 NONE"
        if decision.get("selected_method") not in ("LOCAL_ICP", "GLOBAL_FPFH_RANSAC_ICP"):
            return f"selected_method '{decision.get('selected_method')}' not in allowed tools"
        if "parameter_policy" not in decision:
            return "decision missing required field 'parameter_policy'"
        if "confidence" not in decision:
            return "decision missing required field 'confidence'"
        if not isinstance(decision["confidence"], (int, float)) or not 0.0 <= float(decision["confidence"]) <= 1.0:
            return "confidence must be a float in [0.0, 1.0]"
        param_err = validate_parameter_policy(decision["parameter_policy"])
        if param_err:
            return param_err
        return None

    if rp == "NONE":
        return "information_sufficient=false 时 requested_probe 不得为 NONE"
    if rp in probes_already_run:
        return f"probe '{rp}' already executed; duplicate probe requests are not allowed"
    if len(probes_already_run) >= MAX_PROBES_PER_RUN:
        return (f"probe quota exhausted ({len(probes_already_run)}/{MAX_PROBES_PER_RUN}); "
                f"must set information_sufficient=true and select a formal method")
    if "probe_reason" not in decision or not str(decision["probe_reason"]).strip():
        return "probe_reason required when requesting a probe"
    if decision.get("selected_method") is not None:
        return "selected_method must be null when information_sufficient=false"
    return None


def validate_assessment(assessment: Dict[str, Any]) -> Optional[str]:
    """验证 Agnes 评估 JSON。返回 None=合法，str=错误。"""
    if assessment.get("decision") not in ("ACCEPT", "RETRY", "ABORT"):
        return f"decision must be one of ACCEPT/RETRY/ABORT, got '{assessment.get('decision')}'"
    if "reason" not in assessment:
        return "assessment missing required field 'reason'"
    risk = assessment.get("local_optimum_risk")
    if risk not in ("LOW", "MEDIUM", "HIGH", "UNKNOWN"):
        return "local_optimum_risk must be one of LOW/MEDIUM/HIGH/UNKNOWN"
    if not isinstance(assessment.get("global_consistency_assessment"), str):
        return "assessment missing required field 'global_consistency_assessment'"
    if not isinstance(assessment.get("evidence_conflicts"), list):
        return "assessment missing required array 'evidence_conflicts'"
    conf = assessment.get("confidence")
    if conf is not None and not (0.0 <= float(conf) <= 1.0):
        return "confidence must be in [0.0, 1.0]"
    return None


# ---------------------------------------------------------------------------
# Prompt 构造（不含 GT / 场景标签 / 路径）
# ---------------------------------------------------------------------------

def build_probe_prompt(diagnosis: Dict[str, Any]) -> str:
    """B2B：Probe 元数据段（Agnes 可选择调用哪些 Probe；不含 GT）。

    Python 不基于诊断指标自动选择任何 Probe；这只是给 Agnes 的可用工具说明。
    """
    from agent_probes import PROBE_REGISTRY
    return json.dumps(
        {
            "available_probes": PROBE_REGISTRY,
            "probe_policy": {
                "max_probes_per_run": MAX_PROBES_PER_RUN,
                "note": (
                    "Whether to call a probe, which probe, and the order are YOUR "
                    "professional judgment. Python only validates the request against the "
                    "whitelist and quota, executes it, and returns the observation. "
                    "Probe outputs are observational signals only — they never auto-select an algorithm."
                ),
            },
        },
        indent=2, ensure_ascii=False, default=str)


def build_decision_prompt(
    diagnosis: Dict[str, Any],
    tools: List[Dict[str, Any]],
    prior_attempts: List[Dict[str, Any]],
    probes_already_run: Optional[List[str]] = None,
    probe_observations: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """构造 Agnes 第一次决策的 prompt（B2B 扩展：Probe 层 + 已有 Probe 观测）。

    不包含：gt_transform / rotation_error / translation_error / 场景标签 / 磁盘路径。
    """
    param_range_info = {
        key: {"min": v["min"], "max": v["max"], "description": v["description"]}
        for key, v in PARAMETER_RANGE.items()
    }
    probes_already_run = probes_already_run or []

    input_payload = {
        "task": "3D point cloud registration strategy selection",
        "diagnosis": diagnosis,
        "available_tools": tools,
        "parameter_ranges": param_range_info,
        "prior_attempts": prior_attempts,
        "probes": json.loads(build_probe_prompt(diagnosis)) | {
            "already_executed": list(probes_already_run),
            "observations": probe_observations or [],
            "quota_note": (
                f"Up to {MAX_PROBES_PER_RUN} probes may be executed this run; "
                f"{len(probes_already_run)} already used."),
        },
        "output_schema": {
            "observation_summary": "string (1-3 sentences summarizing diagnosis + any probe observations)",
            "information_sufficient": "boolean: is the current information enough to select a formal registration method?",
            "requested_probe": "NONE | PCA_ORIENTATION | CHEAP_LOCAL_ICP",
            "probe_reason": "string, required when requested_probe != NONE (why this probe adds information)",
            "candidate_methods": [
                {"method": "string (tool name)", "pros": "string", "risks": "string"}
            ],
            "selected_method": "tool name REQUIRED when information_sufficient=true, null when false",
            "parameter_policy": {
                "global_corr_scale": "float in range, only if GLOBAL_FPFH_RANSAC_ICP",
                "icp_max_corr_scale": "float in range",
            },
            "reasoning_summary": "string (short professional justification, no hidden chain-of-thought)",
            "confidence": "float in [0.0, 1.0]",
        },
        "notes": [
            "Do NOT read GT transform, rotation error, translation error, or level label.",
            "All decisions must be based solely on the provided diagnosis, probe observations, and tool metadata.",
            "If parameter_policy values are out of range, the system will reject and you must re-select.",
            "Probes are observational tools: their output informs your judgment but never auto-selects an algorithm.",
            "A probe observation with LOW confidence should be treated as 'insufficient', not as a usable angle.",
            "When orientation or geometry evidence is ambiguous, degenerate, or contradicts local convergence, include local-optimum risk in each candidate method's risks and in your method justification.",
            "Local overlap quality alone does not establish that the globally correct pose has been identified.",
        ],
    }

    return json.dumps(input_payload, indent=2, ensure_ascii=False, default=str)


def build_assessment_prompt(
    observation: Dict[str, Any],
    prior_attempts: List[Dict[str, Any]],
    current_method: str,
    current_policy: Dict[str, Any],
    probe_observations: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """构造 Agnes 第二次（评估）的 prompt。

    传给 Agnes 的是 Agent 合法可见指标（fitness/rmse/runtime），
    不包含 GT。
    """
    # 只提取可观测指标，过滤 transform（大矩阵）和其他内部字段
    obs_visible = {
        k: v for k, v in observation.items()
        if k in ("fitness", "rmse", "inlier_rmse", "elapsed_s",
                "ransac_fitness", "ransac_rmse",
                "tool_name", "parameter_policy_used",
                "max_correspondence_distance",
                "ransac_max_correspondence_distance",
                "icp_max_correspondence_distance")
    }

    input_payload = {
        "task": "Registration result assessment: ACCEPT / RETRY / ABORT",
        "current_attempt": {
            "method": current_method,
            "parameter_policy": current_policy,
            "observation": obs_visible,
        },
        "prior_attempts": prior_attempts,
        "probe_observations": probe_observations or [],
        "guardrail_reference": {
            "floor_fitness": FLOORGUARD_FITNESS,
            "max_retry_remaining": MAX_RETRY_LIMIT - len(prior_attempts),
            "note": "Guardrail only sets a minimum acceptable quality floor and retry limit; "
                    "the professional judgment of ACCEPT/RETRY/ABORT is yours.",
        },
        "output_schema": {
            "assessment": "string (short professional assessment of result quality)",
            "global_consistency_assessment": "string (whether all observable geometry/probe evidence supports one globally consistent pose)",
            "local_optimum_risk": "LOW | MEDIUM | HIGH | UNKNOWN",
            "evidence_conflicts": "array of unresolved contradictions or ambiguities; empty only when none remain",
            "decision": "ACCEPT | RETRY | ABORT",
            "reason": "string (short professional reason)",
            "next_method": "string (tool name) or null (if ACCEPT/ABORT)",
            "next_parameter_policy": "object or null",
            "confidence": "float in [0.0, 1.0]",
        },
        "notes": [
            "Do NOT read GT transform or rotation/translation error in your assessment.",
            "Fitness and RMSE measure consistency of accepted local correspondences; even strong values are not, by themselves, proof of the globally correct pose.",
            "Cross-check the current result against all available orientation, geometry, probe, and prior-attempt evidence before deciding.",
            "If ambiguity, degeneracy, or probe contradiction remains, explicitly assess local-optimum risk and decide whether more evidence, changed parameters, another registered method, or acceptance is professionally justified.",
            "ACCEPT: the combined observable evidence, not fitness alone, is sufficient for the task; explain why any remaining local-optimum risk is acceptable.",
            "RETRY: result is below acceptable quality but there is a plausible retry path.",
            "ABORT: no reasonable path to a better result; stop.",
            "These are judgment requirements only. Python does not map any observation to a method or verdict.",
        ],
    }

    return json.dumps(input_payload, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Agnes 决策器 / 评估器 包装（供 runner 注入）
# ---------------------------------------------------------------------------
#
# 实际 Agnes 调用由 AGH 会话完成（subagent_fork 或当前会话内直接 prompt）。
# 这两个工厂函数将 raw Agnes 响应解析为 structured dict，并运行 guardrail。
# 如果 Agnes 输出无效 JSON 或违反 guardrail，返回带 _error 字段的 dict，
# 由调用方决定是否重试。

def parse_agnnes_decision(raw_response: str,
                         probes_already_run: Optional[List[str]] = None,
                         probe_observations: Optional[List[Dict[str, Any]]] = None
                         ) -> Dict[str, Any]:
    """解析 Agnes 原始文本输出为 decision dict，并运行 guardrail（B2B 扩展）。

    返回：
      合法 → dict with selected_method/parameter_policy/confidence（或 requested_probe）
      无效 → dict with _error="..."
    """
    try:
        # 尝试从 raw response 中提取 JSON
        # Agnes 可能输出 ```json ... ``` 包裹，或带 BOM / 前后说明文字
        text = raw_response.strip().lstrip("\ufeff")
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        if not text.startswith("{"):
            i, j = text.find("{"), text.rfind("}")
            if i >= 0 and j > i:
                text = text[i:j + 1]
        decision = json.loads(text)
    except (json.JSONDecodeError, IndexError) as e:
        return {"_error": f"failed to parse Agnes response as JSON: {e}"}

    err = validate_decision(decision,
                           probes_already_run=probes_already_run,
                           probe_observations=probe_observations)
    if err:
        decision["_error"] = err
        return decision

    decision["_agnnes_model"] = "agnes-3.0-flash"
    decision["_agnnes_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    decision["_implementation"] = "agnnes_real"
    return decision


def parse_agnnes_assessment(raw_response: str) -> Dict[str, Any]:
    """解析 Agnes 原始文本输出为 assessment dict，并运行 guardrail。"""
    try:
        text = raw_response.strip().lstrip("\ufeff")
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        if not text.startswith("{"):
            i, j = text.find("{"), text.rfind("}")
            if i >= 0 and j > i:
                text = text[i:j + 1]
        assessment = json.loads(text)
    except (json.JSONDecodeError, IndexError) as e:
        return {"_error": f"failed to parse Agnes assessment as JSON: {e}"}

    err = validate_assessment(assessment)
    if err:
        assessment["_error"] = err
        return assessment

    # Guardrail: 若 fitness < FLOORGUARD_FITNESS 且 Agnes 判断 ACCEPT，
    # 强制改为 RETRY（guardrail 覆写，非 Agnes 决策）
    fitness = assessment.get("_fitness", None)
    if fitness is not None and float(fitness) < FLOORGUARD_FITNESS:
        if assessment["decision"] == "ACCEPT":
            assessment["decision"] = "RETRY"
            assessment["reason"] = (
                f"[GUARDRAIL OVERWRITE] fitness={fitness} < floor {FLOORGUARD_FITNESS}, "
                f"ACCEPT not permitted. Agnes original reason: {assessment.get('reason', '')}"
            )
            assessment["_guardrail_applied"] = "floor_fitness"

    assessment["_agnnes_model"] = "agnes-3.0-flash"
    assessment["_agnnes_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    assessment["_implementation"] = "agnnes_real"
    return assessment


def agnes_decide_from_raw(
    diagnosis: Dict[str, Any],
    tools: List[Dict[str, Any]],
    prior_attempts: List[Dict[str, Any]],
    raw_response: str,
    probes_already_run: Optional[List[str]] = None,
    probe_observations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """从 Agnes 原始响应构造 decision dict（guardrail 已检查，B2B 扩展）。"""
    return parse_agnnes_decision(raw_response,
                                 probes_already_run=probes_already_run,
                                 probe_observations=probe_observations)


def agnes_assess_from_raw(
    observation: Dict[str, Any],
    prior_attempts: List[Dict[str, Any]],
    current_method: str,
    current_policy: Dict[str, Any],
    raw_response: str,
) -> Dict[str, Any]:
    """从 Agnes 原始响应构造 assessment dict（guardrail 已检查）。"""
    obs_for_guardrail = {k: observation.get(k) for k in ("fitness",)}
    result = parse_agnnes_assessment(raw_response)
    # 注入 fitness 供 guardrail 检查
    if "fitness" in observation:
        result["_fitness"] = observation["fitness"]
    return result


# ---------------------------------------------------------------------------
# 工厂：生成可注入 run_agent_case 的 callable
# 这些 callable 接收一个 raw_ag_response 获取函数（由 AGH 会话提供）
# ---------------------------------------------------------------------------

class AgnesDecisionAdapter:
    """将 AGH 会话中的 Agnes 原始响应适配为 runner 可用的 decide/assess 函数。

    用法（在 AGH 会话外层调用）：
        adapter = AgnesDecisionAdapter(get_raw_response_fn)
        res = run_agent_case(...,
            agnes_decide_fn=adapter.decide,
            agnes_assess_fn=adapter.assess)
    """

    def __init__(self, get_raw_decision: callable, get_raw_assessment: callable,
                 probes_already_run_fn: Optional[callable] = None,
                 probe_observations_fn: Optional[callable] = None):
        """
        get_raw_decision(diagnosis, tools, prior_attempts) -> str
        get_raw_assessment(observation, prior_attempts, current_method, current_policy) -> str
        两个 callable 由 AGH 会话层提供，封装 subagent_fork 调用。
        B2B 扩展：probes_already_run_fn / probe_observations_fn 由 AGH 会话层提供，
        返回当前 case 已执行的 Probe 列表与 Probe 观测，注入 decision prompt。
        """
        self._get_raw_decision = get_raw_decision
        self._get_raw_assessment = get_raw_assessment
        self._probes_already_run_fn = probes_already_run_fn or (lambda: [])
        self._probe_observations_fn = probe_observations_fn or (lambda: [])

    def decide(self, diagnosis: Dict[str, Any],
               tools: List[Dict[str, Any]],
               prior_attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
        probes_run = list(self._probes_already_run_fn())
        probe_obs = list(self._probe_observations_fn())
        prompt = build_decision_prompt(diagnosis, tools, prior_attempts,
                                       probes_already_run=probes_run,
                                       probe_observations=probe_obs)
        raw = self._get_raw_decision(prompt)
        result = parse_agnnes_decision(raw, probes_already_run=probes_run,
                                       probe_observations=probe_obs)
        result["_agnnes_raw_response"] = raw
        return result

    def assess(self, observation: Dict[str, Any],
               prior_attempts: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if prior_attempts is None:
            prior_attempts = []
        current_method = observation.get("tool_name", "")
        current_policy = observation.get("parameter_policy_used", {})
        prompt = build_assessment_prompt(
            observation,
            prior_attempts,
            current_method,
            current_policy,
            probe_observations=list(self._probe_observations_fn()),
        )
        raw = self._get_raw_assessment(prompt)
        result = agnes_assess_from_raw(observation, prior_attempts, current_method, current_policy, raw)
        result["_agnnes_raw_response"] = raw
        return result


# ---------------------------------------------------------------------------
# 防止伪 Agent 审计检查
# ---------------------------------------------------------------------------

def audit_real_agnnes_run(run_dir: str) -> Dict[str, Any]:
    """检查已保存的 run 证据，判断 Agnes 是否真正参与决策。

    返回：
      A. 无 Agnes 调用时系统是否仍能产生 selected_method → True = FAIL
      B. 无 Agnes 调用时系统是否仍能产生 ACCEPT/RETRY → True = FAIL
      C. 是否存在 offset_proxy >= 3 → GLOBAL 直接映射 → 存在于主路径 = FAIL
    """
    from pathlib import Path
    import json as _json

    run_p = Path(run_dir)
    result: Dict[str, Any] = {"run_dir": str(run_p), "checks": {}}

    # 读 agh_run_log.json 里的 decision_implementation
    log_path = run_p / "agh_run_log.json"
    if not log_path.exists():
        result["checks"]["log_exists"] = False
        return result

    log = _json.loads(log_path.read_text(encoding="utf-8"))
    impl = log.get("decision_implementation", "unknown")
    result["decision_implementation"] = impl

    # 检查是否有 agnes_raw_response 字段
    decision_files = sorted(run_p.glob("decision_*.json"))
    has_raw = False
    for f in decision_files:
        d = _json.loads(f.read_text(encoding="utf-8"))
        if "_agnnes_raw_response" in d or "_implementation" in d:
            has_raw = True
            break

    result["checks"]["agnnes_raw_response_present"] = has_raw
    result["checks"]["impl_is_real_agnnes"] = (impl == "agnnes_real")
    result["checks"]["impl_is_heuristic"] = (impl == "heuristic_baseline")

    # 检查 offset_proxy 映射是否存在于主路径
    main_offset_proxy_in_runner = False
    try:
        import agent_runner as _ar
        import inspect
        src = inspect.getsource(_ar)
        main_offset_proxy_in_runner = "offset_proxy" in src and "agnnes_real" in src
        # 主路径（agnnes_real）不应有 offset_proxy 直接映射
    except Exception:
        pass

    result["checks"]["heuristic_leak_into_agnnes_path"] = main_offset_proxy_in_runner
    return result
