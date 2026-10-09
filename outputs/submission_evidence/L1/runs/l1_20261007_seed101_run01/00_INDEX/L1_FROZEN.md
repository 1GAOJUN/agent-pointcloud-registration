# L1 封箱证据包 — L1_FROZEN.md

## 状态
**L1 状态：FROZEN**

## 冻结日期
2026-10-07（本地时区 +08:00）

## 原始 run 路径
`outputs/agent_runs/l1_seed_101/`（原始运行证据，冻结后不得删除/移动/修改）

## Submission evidence 路径
`outputs/submission_evidence/L1/`（本封箱证据包，冻结点为当前已核对完毕的版本）

## 冻结约束
自本声明生成起，L1 seed_101 的以下事实被冻结，后续不因展示需要、美化需要
或"重跑一遍更漂亮"而重新运行或修改：
- Selected Method: `GLOBAL_FPFH_RANSAC_ICP`
- Agent 策略参数: `global_corr_scale = 5.0`, `icp_max_corr_scale = 2.0`
- Agent Verdict: `ACCEPT`
- 可观测指标: fitness = 1.0000, RMSE = 1.0480573452953922e-16, runtime = 0.7089753000000201 s
- 独立 GT 评测: rotation_error = 0.0 deg, translation_error = 1.3877787807814457e-17, success = PASS
- 本次使用的 source/target 点云文件与估计 transform（见
  `03_TOOL_CHAIN/observation_01.json` 与 `06_VISUALS/` 下的图）

## 允许重新运行 L1 的唯一情形
仅限以下三种情况，且每次重新运行必须：
1. 回归测试（regression test，验证代码改动没有破坏既有行为）
2. 发现明确 bug（需先记录 bug 位置与影响范围）
3. 最终复现检查（final reproducibility check）

**且**：任何重新运行必须生成**新的 Run ID**（例如 `l1_seed_101_r2`），
写入新的 `outputs/agent_runs/<新run_id>/` 目录，**绝不覆盖或修改**
`outputs/agent_runs/l1_seed_101/` 及本封箱包中已固化的任何文件。

## 当前封箱包的完整性核对（本次冻结时执行）
- 已逐文件核对：`00_INDEX`/`01_AGH`/`02_AGENT`/`03_TOOL_CHAIN`/
  `04_CONFIG`/`05_VALIDATION`/`06_VISUALS` 各目录内容来自
  `outputs/agent_runs/l1_seed_101/`（原始）与上一轮
  `outputs/submission_evidence/l1_seed_101/`（closeout 整理包），
  均为逐字节复制，未做任何数据修改。
- 本次运行结果中"实际值 vs 用户任务书里给出的期望数字"核对结果：
  - base_scale 0.03389 ✓（实际 0.033892031543267295）
  - RANSAC correspondence ≈ 0.1695 ✓（实际 0.1694601577163365）
  - ICP correspondence ≈ 0.0678 ✓（实际 0.06778406308653459）
  - fitness = 1.0000 ✓
  - RMSE = 1.05e-16 ✓（实际 1.0480573452953922e-16）
  - runtime = 0.709 s ✓（实际 0.7089753000000201 s）
  - rotation error = 0.0 deg ✓
  - translation error ≈ 1.39e-17 ✓（实际 1.3877787807814457e-17）
  - 无任何冲突，未发现需要额外报告的差异。
