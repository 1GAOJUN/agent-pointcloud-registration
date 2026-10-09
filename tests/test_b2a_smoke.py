#!/usr/bin/env python3
"""B2A_SMOKE_TEST — 验证真实 Agnes 调用是否接入。

用法：在 AGH 会话中由 subagent_fork 执行（Agnes 外层编排模式）。
      Python 侧只执行本脚本里的确定性部分（diagnosis + tool dispatch + 证据落盘）。
      Agnes 的两次调用（decision + assessment）通过 AGH 会话完成。

本脚本：
  1. 跑 diagnosis（GT-free）
  2. 打印 decision prompt JSON（供 AGH 会话发送给 Agnes）
  3. 接收 Agnes 的 decision 原始文本（写入 agnnes_raw_decision.json）
  4. 解析 + guardrail 验证
  5. 按 Agnes 选择执行工具
  6. 打印 assessment prompt JSON
  7. 接收 Agnes 的 assessment 原始文本（写入 agnnes_raw_assessment.json）
  8. 解析 + guardrail 验证
  9. 调用 Evaluator（GT 只在此时读取）
  10. 落盘所有证据到 outputs/development_tests/B2A_REAL_AGNES_SMOKE/

不运行 L1/L2 正式实验，不进 RUN_INDEX。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agent_diagnose import diagnose
from agent_tools import TOOL_REGISTRY, run_local_icp, run_global_fpfh_ransac_icp
from agent_evaluator import evaluate_agent_result, save_evaluator_result
import agnnes_agent


def _write_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def main():
    # B2A smoke test 使用 L1 seed_101 已知输入（不作为正式 RUN_INDEX 条目）
    case = PROJECT_ROOT / "outputs" / "ICP" / "L1" / "L1" / "seed_101"
    source_ply = str(case / "source.ply")
    target_ply = str(case / "target.ply")
    gt_npy = str(case / "gt_transform.npy")

    out_dir = PROJECT_ROOT / "outputs" / "development_tests" / "B2A_REAL_AGNES_SMOKE"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()

    # 1. Diagnosis（GT-free）
    diagnosis = diagnose(source_ply, target_ply)
    _write_json(diagnosis, out_dir / "diagnosis.json")
    print(f"[step 1] diagnosis done, base_scale={diagnosis['base_scale']:.6f}")

    # 2. 构造 decision prompt
    decision_prompt = agnnes_agent.build_decision_prompt(diagnosis, TOOL_REGISTRY, [])
    _write_json({"prompt": json.loads(decision_prompt)}, out_dir / "agnnes_decision_prompt.json")
    print("[step 2] decision prompt written → agnnes_decision_prompt.json")
    print(f"  将此 JSON 通过 AGH 会话发送给 Agnes 模型，获取原始文本响应")

    # 3. 读取 Agnes 原始 decision 响应（由 AGH 会话写入文件）
    raw_decision_path = out_dir / "agnnes_raw_decision.json"
    if raw_decision_path.exists():
        raw_decision = raw_decision_path.read_text(encoding="utf-8")
        print(f"[step 3] read Agnes raw decision from {raw_decision_path.name}")
    else:
        print(f"[step 3] agnnes_raw_decision.json not found — write it from AGH session first")
        print("  本脚本在 AGH 会话中运行：Agnes 的响应应已写入该文件")
        return 1

    # 4. 解析 + guardrail 验证
    decision = agnnes_agent.parse_agnnes_decision(raw_decision)
    _write_json(decision, out_dir / "agnnes_decision_parsed.json")
    if "_error" in decision:
        print(f"[step 4] DECISION GUARDRAIL ERROR: {decision['_error']}")
        print("  Agnes 应收到此错误并重新输出，本脚本终止")
        return 2

    method = decision["selected_method"]
    policy = decision["parameter_policy"]
    base_scale = float(diagnosis.get("base_scale", 0.1))
    print(f"[step 4] decision OK: method={method}, policy={policy}, conf={decision.get('confidence')}")

    # 5. 执行工具
    if method == "LOCAL_ICP":
        obs = run_local_icp(
            source_ply, target_ply,
            icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
            base_scale=base_scale,
        )
    elif method == "GLOBAL_FPFH_RANSAC_ICP":
        obs = run_global_fpfh_ransac_icp(
            source_ply, target_ply,
            global_corr_scale=policy.get("global_corr_scale", 5.0),
            icp_max_corr_scale=policy.get("icp_max_corr_scale", 1.0),
            base_scale=base_scale,
        )
    else:
        print(f"[step 5] UNKNOWN METHOD: {method}")
        return 3

    obs_save = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in obs.items()}
    obs_save["tool_name"] = method
    obs_save["parameter_policy_used"] = policy
    _write_json(obs_save, out_dir / "observation_01.json")
    print(f"[step 5] tool executed: fitness={obs['fitness']:.4f}, rmse={obs['rmse']:.6f}")

    # 6. 构造 assessment prompt
    assessment_prompt = agnnes_agent.build_assessment_prompt(
        obs_save, [], method, policy,
    )
    _write_json({"prompt": json.loads(assessment_prompt)}, out_dir / "agnnes_assessment_prompt.json")
    print("[step 6] assessment prompt written → agnnes_assessment_prompt.json")

    # 7. 读取 Agnes 原始 assessment 响应（由 AGH 会话写入文件）
    raw_assessment_path = out_dir / "agnnes_raw_assessment.json"
    if raw_assessment_path.exists():
        raw_assessment = raw_assessment_path.read_text(encoding="utf-8")
        print(f"[step 7] read Agnes raw assessment from {raw_assessment_path.name}")
    else:
        print(f"[step 7] agnnes_raw_assessment.json not found — write it from AGH session first")
        return 4

    # 8. 解析 + guardrail 验证
    assessment = agnnes_agent.parse_agnnes_assessment(raw_assessment)
    assessment["_fitness"] = obs_save.get("fitness")
    _write_json(assessment, out_dir / "agnnes_assessment_parsed.json")
    if "_error" in assessment:
        print(f"[step 8] ASSESSMENT GUARDRAIL ERROR: {assessment['_error']}")
        return 5

    print(f"[step 8] assessment OK: decision={assessment['decision']}, reason={assessment['reason'][:80]}...")

    # 9. Evaluator（GT 只在此时读取）
    evaluator_result = evaluate_agent_result(obs["transform"], gt_npy)
    save_evaluator_result(evaluator_result, str(out_dir / "evaluator_result.json"))
    print(f"[step 9] Evaluator done: success={evaluator_result['success']}, "
          f"rot_err={evaluator_result['rot_err_deg']:.4f}°, "
          f"trans_err={evaluator_result['trans_err']:.6f}")

    # 10. 写证据摘要
    evidence = {
        "test_name": "B2A_REAL_AGNES_SMOKE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "total_elapsed_s": round(time.time() - t0, 2),
        "agnnes_model": "agnes-3.0-flash",
        "case": "L1/seed_101 (development smoke test only, NOT L1/L2 formal run)",
        "decision": {
            "selected_method": method,
            "parameter_policy": policy,
            "confidence": decision.get("confidence"),
            "raw_response_file": "agnnes_raw_decision.json",
            "parsed_response_file": "agnnes_decision_parsed.json",
        },
        "observation": {
            "fitness": obs_save.get("fitness"),
            "rmse": obs_save.get("rmse"),
            "tool_name": method,
        },
        "assessment": {
            "decision": assessment["decision"],
            "reason": assessment["reason"],
            "guardrail_applied": assessment.get("_guardrail_applied"),
            "raw_response_file": "agnnes_raw_assessment.json",
            "parsed_response_file": "agnnes_assessment_parsed.json",
        },
        "evaluator": {
            "success": evaluator_result["success"],
            "rot_err_deg": evaluator_result["rot_err_deg"],
            "trans_err": evaluator_result["trans_err"],
        },
        "gt_isolation_check": "PASS if agnnes_raw_decision/assessment contain no gt_transform/rotation_error/L1/L2 keywords",
        "run_dir": str(out_dir),
    }
    _write_json(evidence, out_dir / "B2A_SMOKE_EVIDENCE.json")
    print(f"\n[done] B2A_SMOKE evidence → {out_dir / 'B2A_SMOKE_EVIDENCE.json'}")
    print(f"  fitness={obs_save.get('fitness')}, gt_success={evaluator_result['success']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
