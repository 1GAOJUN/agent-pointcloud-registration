# 实验台账 EXPERIMENT_LEDGER.md

审计日期：2026-10-06。只读，未重跑实验。
证据等级定义：
- 强：有实际运行输出 + 指标 + 结果文件/日志，可明确证明运行过。
- 中：存在结果文件或日志，但缺部分参数/上下文。
- 弱：仅有脚本/函数/文字描述，无实际运行结果证明。
- 无法判断：存在文件但无法证明与某次运行对应。

日期一栏优先取 JSON/txt 内嵌 timestamp；若无则取 Git 提交时间或文件 mtime（标注“辅助”）。

---

## 台账总表

| ExpID | 实验 | 状态 | 日期 | 场景 | Seed | 输入数据 | 数据特征 | 方法 | 预处理 | 关键参数 | 执行入口 | fitness | RMSE | rot_err | trans_err | runtime | PASS/FAIL | 结果文件 | 可视化 | 日志 | 证据 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E2-L1 | 四关基线 L1 | 已确认运行 | 2026-10-05 13:04 (CSV/ICP mtime) | L1 | 101 | outputs/ICP/L1(source/target) | 小角度干净 | 点到面ICP(单位阵初值) | 法向估计 | thr=0.04,iter=100 | src/run_benchmark.py | 1.0 | — | 1.21e-06° | 1.69e-16 | 2.73s | PASS | outputs/reports/baseline_results.csv 第L1行; outputs/ICP/L1/est_transform.npy,meta.json | ICP/L1/visuals/01_initial.png,02_final_result.png | CSV | 强 | 数据由 run_benchmark 现场生成并落到 outputs/ICP/L1 |
| E2-L2 | 四关基线 L2 | 已确认运行 | 同上 | L2 | 2022→实为202 | outputs/ICP/L2 | 大角度干净 | 点到面ICP(单位阵) | 法向估计 | 同上 | 同上 | 0.134 | — | 124.90° | 0.527 | 4.68s | FAIL | 同上 L2 行 | ICP/L2/visuals | CSV | 强 | 大角度朴素 ICP 发散，符合预期剧情 |
| E2-L3 | 四关基线 L3 | 已确认运行 | 同上 | L3 | 303 | outputs/ICP/L3 | 中角度+噪声+离群 | 点到面ICP(单位阵) | 法向估计 | 同上 | 同上 | 0.3225 | — | 30.64° | 0.341 | 1.33s | FAIL | L3 行 | ICP/L3/visuals | CSV | 强 | target 32400 点(离群+30000) |
| E2-L4 | 四关基线 L4 | 已确认运行 | 同上 | L4 | 404 | outputs/ICP/L4 | 小角度+裁剪30% | 点到面ICP(单位阵) | 法向估计 | 同上 | 同上 | 0.6331 | — | 0.0053° | 9.57e-05 | 1.21s | FAIL | L4 行 | ICP/L4/visuals | CSV | 强 | 旋转几乎对，仅 fitness 未达标(重叠少) |
| E6 | evaluate 自测 | 已确认运行 | 2026-10-04 20:50:56 | — | — | — | — | 内置自测 | — | — | src/evaluate.py | — | — | — | — | — | 4项PASS | outputs/reports/evaluate_test.txt | — | txt | 强 | 验证评测工具本身 |
| E7 | L2 全局对照 | 已确认运行 | 结果文件 mtime 2026-10-05 14:00:21 | L2 | 读 ICP/L2 已有 | outputs/ICP/L2 | 大角度干净 | FPFH+RANSAC+点到面ICP vs 朴素ICP | 法向估计 | RANSAC thr等固化 | tests/test_l2_global_reg.py | 0.134/1.0 | — | 124.87°/≈0° | 0.53/2.8e-17 | 6.85/0.84s | 朴素FAIL/实验PASS | outputs/ICP/L2/l2_global_registration_result.json | ICP/L2/visuals | JSON | 强 | 两策略对照 |
| E8 | L2 闭环调度 | 已确认运行 | mtime 2026-10-05 14:20:53 | L2 | 读 ICP/L2 | outputs/ICP/L2 | 大角度干净 | 朴素ICP→诊断→FPFH+RANSAC+ICP | 法向估计 | 硬编码阈值 | src/pipelines/closed_loop_l2.py | 0.134/1.0 | — | 125.47°/≈0° | 0.527/0.0 | 6.27/0.54s | 基线FAIL/全局PASS | outputs/ICP/L2/l2_closed_loop_result.json | — | JSON | 强 | 含 diagnosis/switch_strategy |
| E9 | L2 SVD+ICP 流水线 | 已确认运行 | 2026-10-05 21:20:20 (json timestamp) | L2 | 读 outputs/L2 | outputs/L2 | 大角度干净 | SVD交叉协方差全局初值 + 点到面ICP | — | SAMPLE_SEED=202,ratio=0.5 | src/l2_pipeline.py | 1.0 | 8.5e-16/2.66e-16 | 2.41e-06° | 0.0 | 0.373/0.035s | PASS | outputs/L2/l2_registration_result.json | L2/visuals(frames) | l2_registration_log.txt | 强 | SVD 直接把大角度初值估准，ICP 秒收敛 |
| E10 | L2 配准动画 | 已确认运行 | frames mtime 2026-10-06 12:04~12:05 | L2 | 读 outputs/L2 | outputs/L2 | 大角度干净 | 关键帧插值(SLERP近似)+matplotlib+ffmpeg | — | N_KEYFRAMES=30,fps=10,sample=0.3 | src/utils/visualize_registration_animation.py | — | — | — | — | — | 生成80帧+mp4 | outputs/L2/visuals/l2_registration_animation.mp4 | L2/visuals/frames/*.png | _concat_list.txt | 强 | 提交后重跑过(帧内容更新) |
| E11 | L3 探测(seed303三策略) | 已确认运行 | mtime 2026-10-06 13:30:09 | L3 | 303(读ICP/L3) | outputs/ICP/L3 | 中角度脏 | icp_naive / icp_robust_outlier / global_registration_robust | SOR离群剔除 | SOR(30,1.0)等 | (临时脚本, 入口未单独留) | 0.3225/0.1986/1.0 | 0.0254/0.0221/0.00495 | 30.64/29.37/0.132° | 0.341/0.365/1.5e-04 | 1.39/3.11/6.99s | 前二FAIL/第三PASS | outputs/L3_probe_existing_seed303.json | ICP/L3/visuals | JSON | 强 | 说明脏数据下鲁棒全局可救 |
| E12 | L3 复现(303/505/707) | 已确认运行 | mtime 2026-10-06 13:37:19 | L3 | 303/505/707 | data/L3, data/L3_new | 中角度脏 | icp_naive→global_registration_robust+候选姿态检查 | SOR | 同上 | (临时脚本) | 见JSON | 0.0049~0.0104 | 见JSON | 见JSON | 4.46/4.20/5.48s | g1PASS/g2FAIL/g3FAIL | outputs/L3_reproduction_summary.json + 3 final npy + L3_repro_seeds.json | — | JSON | 强 | 仅seed303稳定；505/707失败，暴露对称/翻转解 |
| E13 | L3 SVD+ICP 新流水线 | 仅有代码 | 文件mtime 2026-10-06 13:45:58(辅助) | L3 | — | outputs/ICP/L3 | 中角度脏 | SOR+SVD全局初值+点到面ICP | SOR | 复用svd_global_init_new/icp_naive_new | src/algorithms/l3_svd_icp_pipeline.py | — | — | — | — | — | 无结果 | 无 | 无 | 无 | 弱 | 未找到运行输出 |
| E14 | L2 preview 图 | 疑似运行(未落盘) | _gen_preview.py mtime 2026-10-06 12:20(辅助) | L2 | — | outputs/L2 | 大角度 | OffscreenRenderer 4 张预览 | — | — | _gen_preview.py | — | — | — | — | — | 无结果 | outputs/L2/visuals/preview/(空) | 空 | 无 | 弱 | preview 目录为空，_coarse_sim.npy 存在 |
| E15 | L3 临时评测日志 | 无法判断 | _tmp_eval_l3.log mtime 2026-10-06 13:26(0字节) | L3 | — | — | — | 未知 | — | — | _tmp_eval_l3.log / _tmp_check_rot.py | — | — | — | — | — | 无 | 无 | 0字节日志 | 无 | 日志为空 |

---

## 逐条补充说明

### E1 最小配准 demo（register_minimal.py）
- 状态：代码存在于 7da9350 提交，但在 440dece 提交中被删除（register_minimal.py 从 git 移除）。当前工作目录无此文件。
- 文档记载（工作流程总结 阶段3）：“可独立运行 register_minimal.py，旋转误差≈0.000002°，平移≈0m，前后截图输出到 outputs”。
- 结论：历史强证据（Git 内有过代码+文档记载），当前无文件；无对应留存的独立结果 JSON。证据等级：中。
- 备注：README 仍引用 register_minimal.py 作为“最简 demo（保留作回归纪念）”，但文件已删——文档与仓库不一致。

### E3 L1 回归测试（test_regression_l1.py）
- 有脚本 + __pycache__/test_regression_l1.cpython-311.pyc（mtime 2026-10-04 21:22，说明被 import/运行过）。
- 运行的是“临时目录跑 L1 一整关”，不落盘独立结果（用 tempfile）。无独立输出文件。
- 证据等级：中（编译记录+文档记载，但无留存的指标文件）。

### E4 真值自验 verify_gt.py / E5 剧情自验 verify_story.py
- 均有脚本+pyc（10/5 13:03 / 10/4 21:22）。文档记载“误差1e-16量级”“L1过L2败剧情自洽”。
- verify_story 直接读 outputs/reports/baseline_results.csv，其结论依附于 E2 的 CSV。
- 证据等级：中。

### E11/E12 执行入口说明
- 这两个 L3 实验的结果 JSON 结构（含 diagnosis/switch_strategy/candidate_results）与 closed_loop 风格一致，推测由临时探索脚本（未留在仓库，可能已被删）产生。仓库当前没有对应的可执行入口脚本（_tmp_eval_l3.log 为空）。
- 因此“执行入口”一栏写“临时脚本，入口未单独留存”，这本身就是一个证据缺口。

### 同一实验多版本
- L2 存在三套不同流水线：FPFH+RANSAC(E7/E8)、SVD+ICP(E9)、动画(E10)，均针对 L2 成功但方法不同，本台账分开记录、不合并。
- L3 存在探测(E11)与复现(E12)两代，且 E12 内部 3 个 seed 分别记录；l3_svd_icp_pipeline(E13) 为第三个未验证版本，单独记录。
