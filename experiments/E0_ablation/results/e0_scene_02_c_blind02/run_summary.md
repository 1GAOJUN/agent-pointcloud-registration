# Agent 配准闭环运行总结 (run_summary.md)

- Agnes 模型: agnes-3.0-flash (version 2026-10-06)
- 运行时间: 2026-10-08 19:05:32
- 运行 ID: e0_scene_02_c_blind02 (variant=REAL_AGNES_NO_PROBE, case=scene_02, frozen_seed=1002)
- Agent 尝试次数: 1
- 最终 Agent 判断: ACCEPT
- 最终所选工具: GLOBAL_FPFH_RANSAC_ICP
- Agent 可观测 fitness: 1.0

## GT 独立评测（仅在 Agent 决策后由 Evaluator 读取）
- rotation_error_deg = 0
- translation_error = 5.55112e-17
- success = True
- 阈值: rot<5.0°, trans<0.05

## 各步
- step 1: tool=GLOBAL_FPFH_RANSAC_ICP policy={'global_corr_scale': 5.0, 'icp_max_corr_scale': 2.0} -> ACCEPT
