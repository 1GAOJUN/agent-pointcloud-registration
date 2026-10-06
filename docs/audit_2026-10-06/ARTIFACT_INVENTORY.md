# 可提交证据 / 素材清单 ARTIFACT_INVENTORY.md

审计日期：2026-10-06。只读整理，未新增任何实验产物。
每条注明：路径 / 内容 / 能证明什么 / 是否足以用于最终提交 / 若不足缺什么。

---

## A. 数据证据（CSV / JSON / TXT / metrics）

1. outputs/reports/baseline_results.csv
   - 内容：L1/L2/L3/L4 四关朴素 ICP 基线的 rot_err、trans_err、fitness、elapsed、PASS/FAIL。
   - 可证明：朴素 ICP 在 L1 通过、L2/L3/L4 失败（“失败表”故事线的数值依据）。
   - 是否足够：足够作为“Baseline 0”量化证据。
   - 缺：多 seed 均值/方差、角度/噪声/裁剪扫描曲线（v1.4 P3 未做）。

2. outputs/reports/evaluate_test.txt
   - 内容：evaluate.py 内置自测 4 项（identity / pure_rotation_30_z / pure_translation / combined），all_passed True。
   - 可证明：评测“尺子”本身正确（真值验证工具可信）。
   - 是否足够：足够（评测工具自检）。

3. outputs/ICP/L2/l2_global_registration_result.json
   - 内容：L2 朴素 ICP vs FPFH+RANSAC+ICP 对照，实验组 rot≈0/fitness=1.0 PASS。
   - 可证明：L2 大角度用全局配准可救到达标（算法有效性）。
   - 是否足够：足够作为 L2 单场景算法证据。
   - 缺：多 seed 复现、无 GT 的 Agent 视角版本。

4. outputs/ICP/L2/l2_closed_loop_result.json
   - 内容：L2 闭环（baseline FAIL → global PASS，含 diagnosis 文本、switch_strategy=True、总耗时）。
   - 可证明：“执行→失败→诊断→切换→复验”的算法闭环流程可自动跑通。
   - 是否足够：作为“脚本化闭环”证据足够；但作为“Agent 自主决策”证据不足（见 D 类）。
   - 缺：模型参与的 decision trace。

5. outputs/L2/l2_registration_result.json + l2_registration_log.txt + est_transform.npy
   - 内容：L2 SVD全局初值+ICP 两阶段指标、阶段日志、最终变换矩阵。
   - 可证明：SVD 交叉协方差法对干净大角度可精确估初值，ICP 秒级收敛（强证据，含 timestamp 2026-10-05 21:20:20）。
   - 是否足够：足够。
   - 缺：脏数据下 SVD 初值是否仍有效（L3 场景 E13 未验证）。

6. outputs/L3_probe_existing_seed303.json
   - 内容：L3 seed303 三策略（icp_naive / icp_robust_outlier / global_registration_robust）指标，第三策略 PASS（rot 0.132°/fitness 1.0）。
   - 可证明：脏数据下鲁棒 FPFH+RANSAC 全局配准可救到达标。
   - 是否足够：单 seed 足够作“可达标”证据；作为稳定性证据不足。
   - 缺：多 seed、与 icp_multistart 的公平对比。

7. outputs/L3_reproduction_summary.json + L3_repro_seeds.json + 3 个 L3_repro_final_*.npy
   - 内容：L3 三组（seed303/505/707）“朴素ICP→鲁棒全局+候选姿态检查”完整复现，含各候选姿态(rot/inv/Z翻转)结果。
   - 可证明：L3 在 seed303 稳定达标；seed505/707 未达标，暴露对称/翻转解问题。
   - 是否足够：作为“L3 现状（部分稳定）”证据足够；作为“L3 已完成”不足。
   - 缺：对 505/707 的修复验证、成功 case 的 after/compare 图。

8. configs/L1~L4.yaml + 各 data/、outputs/ICP/*、meta.json
   - 内容：四关参数定义 + 生成数据的元信息（seed、点数、config、generated_at）。
   - 可证明：实验参数可复现（固定 seed）。
   - 是否足够：作为可复现配置足够。
   - 缺：与 L2_new/L3_new 多份数据的对应关系说明。

---

## B. 图片证据（before / after / compare / 曲线 / 截图）

1. outputs/ICP/L1~L4/visuals/01_initial.png 与 02_final_result.png（共 8 张）
   - 内容：每关“配准前 source/target 叠加”与“source 经 est_transform 变换后与 target 对齐”对比图。
   - 可证明：四关基线的视觉前后对比（L1 对齐、L2/L3/L4 错位）。
   - 是否足够：作为基线静态图足够；但 L2/L3/L4 的“成功补救后”静态图缺失（补救结果只有 JSON，无对应 after 图）。
   - 缺：L2/L3 成功 case 的 before/after/compare 三件套、同视角标注。

2. data/L1/seed_001/visualize_before.png
   - 内容：make_data 默认 3-seed 生成 L1 seed_001 的 source/target 并排图。
   - 可证明：数据生成器能出可视化（注意此 seed_001 与 configs 的 seed_101 是不同数据）。
   - 是否足够：作为数据生成示意足够。
   - 缺：与 configs 正式 seed 对应的一致图。

3. outputs/L2/visuals/frames/frame_000~079.png
   - 内容：L2 配准过程 80 帧（初始错位 → 插值 → 最终对齐，左右双视图）。
   - 可证明：L2 配准过程的可视化素材。
   - 是否足够：作为动画帧素材足够。
   - 缺：frame_031~079 与 mp4 在 440dece 提交后重跑过（内容不同），需确认以哪一版为准。

---

## C. 视频证据（动画 / 录屏）

1. outputs/L2/visuals/l2_registration_animation.mp4
   - 内容：由 frames 用 ffmpeg 合成的 L2 配准动画（libx264）。
   - 可证明：配准过程可做成可播放动画。
   - 是否足够：作为“L2 演示动画”素材足够。
   - 缺：3–5 分钟正式演示视频（含 AGH 决策日志分屏）尚未制作；mp4 在提交后重跑过，需定稿。

---

## D. AGH 运行证据（Agent 日志 / 工具调用链 / 模型参与记录）

- 现状：仓库内没有任何 AGH/Agnes 模型参与配准决策的落盘证据文件（无 agent 会话日志、无 tool-call 链 JSON、无 decision trace、无“模型参与核心任务”记录）。
- 可证明什么：目前无法证明“AGH 驱动自主决策”这一核心主张。
- 是否足够：不足。
- 缺什么（关键缺口）：
  1) 至少 1 条完整的 AGH 工具调用链（诊断工具→算法工具→评测工具）截图/导出；
  2) Agnes 模型参与核心配准决策的会话记录（体现“自主判断”而非脚本 if-else）；
  3) 结构化 decision_trace（observation/diagnosis/candidate_methods/selected_method/parameter_rationale/result_metrics/confidence/final_decision）；
  4) Agent 与 Evaluator 隔离的运行证据（Agent 不读 GT）。
- 说明：docs（参赛方案 v1.4、项目说明 v1.2）把以上列为“待补/进行中标题”，与仓库现状一致——这些能力尚未实现与留证。

---

## E. 可复现证据（运行脚本 / requirements / 配置 / README）

1. requirements.txt（open3d==0.20.0, numpy==1.26.4, matplotlib==3.8.4）
   - 可证明：依赖可复现。是否足够：足够（作为第三方组件申报基础）。

2. src/run_benchmark.py（四关基线一键入口）、src/evaluate.py、src/make_data.py
   - 可证明：数据生成→基线配准→评测主流程可一键复现。是否足够：足够（Baseline 0 可复现）。

3. configs/L1~L4.yaml
   - 可证明：参数固化可复现。是否足够：足够。

4. README.md
   - 内容：项目门面 + 目录结构 + 运行命令。
   - 问题：仍引用已被删除的 register_minimal.py、旧 outputs 结构；与当前仓库（algorithms/pipelines/quarantine、L2/L3 输出、v1.4 文档）不一致。
   - 是否足够：作为门面不足，需与现状对齐。

5. tests/（test_regression_l1 / verify_gt / verify_story / test_l2_global_reg / test_closed_loop_l2）
   - 可证明：有正常/边界/失败三类测试样例的雏形（L1 回归=正常，verify_story 的 L2 失败=失败样例，L2 对照=正常对照）。
   - 是否足够：部分足够；缺统一的“正常/边界/失败”标准样例文档与 L3/L4 对应测试。

---

## 提交就绪度小结
- 已可直接用于提交：A 类 1/2/4/5/7/8，B 类 1，C 类 1（注意 L2 帧/视频需定稿版本），E 类 1/2/3。
- 尚不足（需补或需定稿）：A 类 3/6（多 seed 与 L3 稳定性）、B 类 3（L2 帧版本定稿）、C 类（正式 3–5 分钟视频未做）、D 类全部（AGH 自主决策证据，最关键缺口）、E 类 4/5（README 与测试样例文档）。
