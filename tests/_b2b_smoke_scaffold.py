"""B2B Active Probe Smoke Test — 脚手架（Python 确定性部分）。

用法：在 AGH 会话中执行（Agnes 外层编排模式）。本脚本只跑 Python 侧确定性部分：
  1. diagnosis（GT-free）→ diagnosis.json
  2. 构造 decision prompt（含 Probe 层 + probe_observations=[]）→ agnnes_decision_prompt_01.json
  3. AGH 会话把 prompt 发给 Agnes，将 Agnes 原始文本响应写入 agnnes_raw_decision_01.json
  4. 本脚本解析 decision：
     - information_sufficient=true → 直接选工具（进入正式 ICP/评估）
     - information_sufficient=false → 按 requested_probe 执行 Probe（白名单+去重+配额校验），
       落盘 probe_observation_NN.json + probe_prompt_NN.json，
       把 Probe 观测回灌到二次 decision prompt（agnnes_decision_prompt_02.json），
       AGH 会话再次发给 Agnes → agnnes_raw_decision_02.json
  5. 工具执行（按 Agnes 最终 selected_method）→ observation_01.json
  6. assessment prompt（含 probe_observations）→ AGH 会话发给 Agnes → agnnes_raw_assessment.json
  7. Evaluator（GT 只在 Agent 停止后读取）→ evaluator_result.json
  8. 证据摘要 B2B_SMOKE_EVIDENCE.json

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
from agent_probes import PROBE_DISPATCH, MAX_PROBES_PER_RUN, run_pca_orientation_probe
from agent_evaluator import evaluate_agent_result, save_evaluator_result
import agnnes_agent


def _write_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def main() -> int:
    case = PROJECT_ROOT / "outputs" / "ICP" / "L1" / "L1" / "seed_101"
    source_ply, target_ply = str(case / "source.ply"), str(case / "target.ply")
    gt_npy = str(case / "gt_transform.npy")

    out_dir = PROJECT_ROOT / "outputs" / "development_tests" / "B2B_ACTIVE_PROBE_SMOKE"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # ---- 1. Diagnosis（GT-free） ----
    diagnosis = diagnose(source_ply, target_ply)
    _write_json(diagnosis, out_dir / "diagnosis.json")
    print(f"[1] diagnosis base_scale={diagnosis['base_scale']:.6f}")

    probes_run: list[str] = []
    probe_obs: list[dict] = []

    # ---- 2. 第一次 decision prompt（无 Probe 观测） ----
    prompt1 = agnnes_agent.build_decision_prompt(diagnosis, TOOL_REGISTRY, [])
    _write_json({"prompt": json.loads(prompt1)}, out_dir / "agnnes_decision_prompt_01.json")
    print("[2] decision prompt 01 written")

    # ---- 3. 读取 Agnes 第一次原始响应（AGH 会话写入） ----
    raw1_path = out_dir / "agnnes_raw_decision_01.json"
    if not raw1_path.exists():
        print(f"[3] {raw1_path.name} not found — AGH session must write it first; stopping here")
        return 1
    raw1 = raw1_path.read_text(encoding="utf-8")
    decision = agnnes_agent.parse_agnnes_decision(raw1, probes_already_run=[])
    _write_json(decision, out_dir / "agnnes_decision_01_parsed.json")
    if "_error" in decision:
        print(f"[3] DECISION GUARDRAIL ERROR: {decision['_error']}")
        return 2
    print(f"[3] decision01: sufficient={decision['information_sufficient']} "
          f"requested_probe={decision.get('requested_probe')}")

    # ---- 4. Probe 循环（最多 2 轮；每轮都必须基于 Agnes 的 requested_probe） ----
    final_decision = None
    round_no = 0
    while True:
        round_no += 1
        # 本轮的 decision：首次用 raw1，之后读 agnnes_raw_decision_NN.json
        if round_no == 1:
            decision = agnnes_agent.parse_agnnes_decision(raw1, probes_already_run=probes_run)
        else:
            raw_n_path = out_dir / f"agnnes_raw_decision_{round_no:02d}.json"
            if not raw_n_path.exists():
                print(f"[4] {raw_n_path.name} not found — AGH session must write it first; stopping")
                return 1
            raw_n = raw_n_path.read_text(encoding="utf-8")
            decision = agnnes_agent.parse_agnnes_decision(
                raw_n, probes_already_run=probes_run, probe_observations=probe_obs)
        _write_json(decision, out_dir / f"agnnes_decision_{round_no:02d}_parsed.json")
        if "_error" in decision:
            print(f"[4] round {round_no} DECISION GUARDRAIL ERROR: {decision['_error']}")
            return 2
        print(f"[4] round{round_no}: sufficient={decision['information_sufficient']} "
              f"requested_probe={decision.get('requested_probe')}")

        if decision["information_sufficient"]:
            final_decision = decision
            break

        # 请求 Probe：白名单 + 去重 + 配额校验
        probe_name = decision["requested_probe"]
        if probe_name not in PROBE_DISPATCH:
            print(f"[4] invalid requested_probe '{probe_name}' — dispatch not allowed"); return 3
        if probe_name in probes_run:
            print(f"[4] duplicate probe request '{probe_name}' blocked by guardrail"); return 3
        if len(probes_run) >= MAX_PROBES_PER_RUN:
            print(f"[4] probe quota ({MAX_PROBES_PER_RUN}) exhausted; "
                  "Agnes must select a formal method on the next round")
            # 配额用尽：把该 decision 原样返回给 Agnes（提示配额耗尽），
            # 下一轮 Agnes 应给 information_sufficient=true；若仍请求 Probe 则终止
            decision._quota_exhausted = True
            final_decision = None
            continue
        if probe_name == "PCA_ORIENTATION":
            obs = run_pca_orientation_probe(source_ply, target_ply)
        else:
            obs = PROBE_DISPATCH[probe_name](source_ply, target_ply,
                                             base_scale=float(diagnosis.get("base_scale", 0.1)))
        obs["_probe_request"] = {
            "probe_name": probe_name,
            "requested_by": "agnnes_real",
            "probe_reason": decision.get("probe_reason"),
        }
        probes_run.append(probe_name)
        probe_obs.append(obs)
        _write_json(obs, out_dir / f"probe_observation_{len(probes_run):02d}.json")
        print(f"[4] probe {probe_name} done → probe_observation_{len(probes_run):02d}.json")

        # 配额耗尽且 Agnes 仍请求 Probe（continue 分支）：下一轮 Agnes 必须给方法；
        # 若再次请求 → 终止（防止无限循环）
        if len(probes_run) >= MAX_PROBES_PER_RUN:
            raw_next_path = out_dir / f"agnnes_raw_decision_{round_no + 1:02d}.json"
            if not raw_next_path.exists():
                print(f"[4] {raw_next_path.name} not found (quota exhausted round); "
                      f"AGH session must write it first; stopping")
                return 1
            raw_next = raw_next_path.read_text(encoding="utf-8")
            decision = agnnes_agent.parse_agnnes_decision(
                raw_next, probes_already_run=probes_run, probe_observations=probe_obs)
            round_no += 1
            _write_json(decision, out_dir / f"agnnes_decision_{round_no:02d}_parsed.json")
            if "_error" in decision:
                print(f"[4] post-quota decision GUARDRAIL ERROR: {decision['_error']}")
                return 4
            if not decision["information_sufficient"]:
                print("[4] Agnes still requesting a probe after quota exhausted — stopping")
                _write_json({"stopped_at": "quota_exhausted_probe_request", "decision": decision},
                            out_dir / "smoke_stop_report.json")
                return 0
            final_decision = decision
            break

    # 每轮 Probe 执行后把观测回灌到下一轮 decision prompt
    if probes_run:
        prompt2 = agnnes_agent.build_decision_prompt(
            diagnosis, TOOL_REGISTRY, [],
            probes_already_run=probes_run, probe_observations=probe_obs)
        _write_json({"prompt": json.loads(prompt2)}, out_dir / f"agnnes_decision_prompt_{min(round_no, 99):02d}.json")

    # ---- 5. 工具执行（按 Agnes 最终 selected_method） ----
    method = final_decision["selected_method"]
    policy = final_decision.get("parameter_policy", {})
    base_scale = float(diagnosis.get("base_scale", 0.1))
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
        print(f"[5] UNKNOWN METHOD: {method}"); return 5
    obs_save = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in obs.items()}
    obs_save["tool_name"] = method
    obs_save["parameter_policy_used"] = policy
    _write_json(obs_save, out_dir / "observation_01.json")
    print(f"[5] tool {method} executed: fitness={obs['fitness']:.4f}")

    # ---- 6. Assessment prompt（含 probe_observations） ----
    aprompt = agnnes_agent.build_assessment_prompt(obs_save, [], method, policy,
                                                   probe_observations=probe_obs)
    _write_json({"prompt": json.loads(aprompt)}, out_dir / "agnnes_assessment_prompt.json")
    rawa_path = out_dir / "agnnes_raw_assessment.json"
    if not rawa_path.exists():
        print(f"[6] {rawa_path.name} not found — AGH session must write it first; stopping")
        return 1
    rawa = rawa_path.read_text(encoding="utf-8")
    assessment = agnnes_agent.agnes_assess_from_raw(obs_save, [], method, policy, rawa)
    _write_json(assessment, out_dir / "agnnes_assessment_parsed.json")
    if "_error" in assessment:
        print(f"[6] ASSESSMENT GUARDRAIL ERROR: {assessment['_error']}"); return 6
    print(f"[6] assessment: {assessment['decision']}")

    # ---- 7. Evaluator（GT 只在此时读取） ----
    ev = evaluate_agent_result(obs["transform"], gt_npy)
    save_evaluator_result(ev, str(out_dir / "evaluator_result.json"))
    print(f"[7] evaluator success={ev['success']} rot_err={ev['rot_err_deg']:.4f}°")

    # ---- 8. 证据摘要 ----
    evidence = {
        "test_name": "B2B_ACTIVE_PROBE_SMOKE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "total_elapsed_s": round(time.time() - t0, 2),
        "agnnes_model": "agnes-3.0-flash",
        "case": "L1/seed_101 (development smoke test only, NOT L1/L2 formal run)",
        "probes_requested_by_agnnes": probes_run,
        "probe_observations": [
            {k: v for k, v in p.items() if k != "_probe_request"} | {"_probe_request": p["_probe_request"]}
            for p in probe_obs
        ],
        "final_decision": {
            "selected_method": method,
            "parameter_policy": policy,
            "confidence": final_decision.get("confidence"),
            "information_sufficient": final_decision.get("information_sufficient"),
            "raw_response_file": f"agnnes_raw_decision_{round_no:02d}.json",
            "parsed_response_file": f"agnnes_decision_{round_no:02d}_parsed.json",
        },
        "observation": {"fitness": obs_save.get("fitness"), "rmse": obs_save.get("rmse"), "tool_name": method},
        "assessment": {"decision": assessment["decision"],
                       "guardrail_applied": assessment.get("_guardrail_applied"),
                       "raw_response_file": "agnnes_raw_assessment.json"},
        "evaluator": {"success": ev["success"], "rot_err_deg": ev["rot_err_deg"], "trans_err": ev["trans_err"]},
        "gt_isolation_check": "PASS if all agnnes_raw_* contain no gt_transform/rotation_error/L1/L2 keywords; Evaluator ran only after Agent stop",
        "anti_fake_probe_check": "PASS only if no probe executed without a corresponding agnnes_raw_decision requesting it; Python never auto-selects probes",
        "run_dir": str(out_dir),
    }
    _write_json(evidence, out_dir / "B2B_SMOKE_EVIDENCE.json")
    print(f"\n[done] B2B smoke evidence → {out_dir / 'B2B_SMOKE_EVIDENCE.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
