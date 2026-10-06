# 新增模块与历史变化总结 FILE_CHANGE_SUMMARY.md

审计日期：2026-10-06。只读总结，未改动任何文件。
依据：Git 提交（7da9350 引入初版、440dece 引入 L2/L3 闭环）、当前目录事实。
原则：只列有项目意义的内容，不逐条列 pyc / 缓存 / 临时文件。

---

## 1. 数据生成
- 文件：src/make_data.py
- 功能：合成“球+偏移盒+圆柱”非对称拼接点云；施加已知刚体变换；支持噪声(sigma)、离群点(ratio)、半空间裁剪(crop)退化；保存 source/target PLY、gt_transform.npy、meta.json；可选真实数据集(bunny/ficus，未实际用)；内置 visualize_pair 出 before 图。
- 是否实际使用：是。run_benchmark 用它现场生成 outputs/ICP/Lx；data/L1、L2_new、L3、L3_new 均为其产物。
- 有什么输出：data/ 与 outputs/ICP/Lx/ 下的 source/target/gt/meta。
- 证据：outputs/ICP/L1~L4/meta.json 的 generated_at 时间戳、data/*/meta.json。

## 2. 评测
- 文件：src/evaluate.py
- 功能：旋转误差(迹法)、平移误差、judge_success(双阈值)、evaluate_case/evaluate_case_dir、合法刚体验证、内置自测并落盘报告。
- 是否实际使用：是（被 run_benchmark、各 tests、l2_pipeline 复用）。
- 有什么输出：outputs/reports/evaluate_test.txt（4 项 PASS）。
- 证据：evaluate_test.txt 时间戳 2026-10-04 20:50:56。

## 3. 配准算法
- 文件：
  - src/algorithms/icp_naive.py：单位阵初值点到面 ICP（L2/L3 基线初测）。实际用于 E11。
  - src/algorithms/icp_naive_new.py：全新封装点到面 ICP（统一 register 接口，参数 MAX_CORR_DIST=0.1/iter=50）。被 l2_pipeline、l3_svd_icp_pipeline 调用（E9 实际用到）。
  - src/algorithms/svd_global_init_new.py：SVD 交叉协方差全局初值（干净数据极准）。E9 核心。
  - src/algorithms/global_registration_robust.py：SOR 离群剔除 + FPFH + RANSAC(放宽 thr=0.5) + 点到面 ICP。E11/E12 实际成功策略。
  - src/algorithms/icp_robust_outlier.py：SOR + 单位阵初值点到面 ICP（L3 对照，实测仍失败）。E11 用到。
  - src/algorithms/l3_svd_icp_pipeline.py：SOR + SVD 初值 + ICP（新，无运行证据）。
  - src/algorithms/quarantine/global_registration.py：L2 版 FPFH+RANSAC+点到面 ICP（干净数据 thr=0.1）。E7/E8 实际调用。命名“quarantine”但为核心算法，命名混淆。
  - src/algorithms/quarantine/icp_multistart.py：多初值(离散 Z 轴 0/90/180/270)点到面 ICP，取 fitness 最高者。被 playbook_v1.0 推荐但当前 L3 实际结果未用它，无独立运行证据。
- 是否实际使用：见上；quarantine/icp_multistart 与 l3_svd_icp_pipeline 未确认被实际跑出结果。
- 有什么输出：由调用方 JSON/npz 承载（见台账 E7~E12）。
- 证据：各 JSON 的 strategy 字段、pyc 时间戳。

## 4. 测试脚本
- 文件：
  - tests/test_regression_l1.py：L1 配置加载→临时目录跑 ICP→阈值判定（正常样例）。有中证据(pyc)。
  - tests/verify_gt.py：真值合法性自验（边界验证）。中。
  - tests/verify_story.py：读 CSV 判 L1 过/L2 败（失败样例验证）。中。
  - tests/test_l2_global_reg.py：L2 朴素ICP vs FPFH+RANSAC+ICP 对照（E7 入口）。强（有输出 JSON）。
  - tests/test_closed_loop_l2.py：跑 closed_loop_l2 出结构化报告（E8 入口）。强（有输出 JSON）。
- 是否实际使用：E7/E8 强；L1 回归/verify 中。
- 证据：对应输出 JSON 的 existence + pyc。

## 5. AGH / Agent 相关
- 文件：src/pipelines/closed_loop_l2.py（“闭环调度器”：朴素ICP→失败诊断→全局补救→复验，输出 ClosedLoopReport）。
- 功能：把 L2 的“失败-切换-复验”固化为可自动执行的调度，含诊断文本与 switch_strategy 标记。
- 是否实际使用：是（E8 有输出 JSON）。
- 关键说明：这是“Python 脚本化的策略闭环”，不是 Agnes 模型在 AGH 运行时做的自主决策。仓库中没有任何 AGH 会话/工具调用/decision trace 落盘。项目说明 v1.2 与参赛方案 v1.4 中“AGH 决策层”“Agent 不可读 GT”“参数自适应”均为规划/待办，未实现、未留证。
- 证据：l2_closed_loop_result.json（强，证明脚本闭环）；无 AGH 模型参与证据（缺口）。

## 6. playbook / 文档
- 文件：
  - docs/playbook_v1.0.md：L2+L3 诊断决策总手册（诊断模式→策略映射，引用实测数值）。
  - quarantine/docs/playbook_l2.md：旧版仅 L2 的 playbook（被 v1.0 取代，仍保留）。
  - docs/AGH驱动的点云自动配准智能体_参赛方案_v1.4.md：参赛执行蓝图/交接档案/评分维度映射/排期（v1.4 重心：未知输入下的诊断-决策-参数自适应-可信度判断闭环）。
  - docs/AGH驱动的点云自动配准智能体_项目说明_v1.2.md：提交用“基本信息+技术信息”母稿，未定项标【待补】。
  - docs/点云配准Agent参赛方案-v1.3.md：前版方案（含四层深度体系、实验矩阵升级、L3 消融设计）。
  - docs/工作流程总结.md：按日工作流（AGH 环境、conda、git 流程、踩坑记录）。
  - docs/status.md：当前状态速记（含 L2/L3 标签漂移提醒）。
- 是否实际使用/一致：playbook_v1.0 推荐的 L3 策略(icp_multistart)与实际成功策略(global_registration_robust)不一致；README 与当前仓库结构/新文档不完全对齐。
- 证据：文件存在；一致性为审计判断（非“实际运行”证据）。

## 7. 可视化
- 文件：
  - src/visualize_all_cases.py：批量为四关出 01_initial/02_final_result.png（E2 配套）。强（8 图存在）。
  - src/utils/visualize_registration_animation.py：L2 关键帧插值动画（matplotlib 出帧 + ffmpeg 合 mp4）。强（80 帧+mp4 存在，E10）。
  - _gen_preview.py（根目录临时脚本）：用 Open3D OffscreenRenderer 出 L2 4 张预览图（INITIAL/COARSE/REFINE/FINAL）。弱：outputs/L2/visuals/preview/ 为空，疑似未成功/未落盘。
- 有什么输出：ICP/* 静态 8 图；L2 动画帧 80 + mp4；preview 目录空。
- 证据：文件存在性 + Git（440dece 引入帧与 mp4，后重跑）。

## 8. 实验结果（汇总层）
- 文件：
  - outputs/reports/baseline_results.csv（四关基线汇总，E2）。
  - outputs/ICP/L2/l2_global_registration_result.json（E7）、l2_closed_loop_result.json（E8）。
  - outputs/L2/l2_registration_result.json + log（E9）。
  - outputs/L3_probe_existing_seed303.json（E11）、L3_reproduction_summary.json + L3_repro_seeds.json + 3 final npy（E12）。
- 功能：把各次运行的量化指标（rot/trans/fitness/rmse/elapsed/PASS-FAIL/诊断/策略切换）结构化落盘。
- 是否实际使用：全部为真实运行产物（强证据来源）。
- 证据：JSON 内嵌 timestamp / 各步 metric。

---

## 历史变化要点（按时间）
- 10/4 23:47-23:56（7da9350/d4c6b55）：造轮子+尺子。引入 make_data/evaluate/run_benchmark/configs L1-L4/测试/初版 outputs（L1~L4 meta、before/after.png、baseline_results.csv、evaluate_test.txt、register_minimal.py）。
- 10/6 00:07（440dece）：L2,L3 闭环。删除 register_minimal.py 与 outputs 根 before/after.png、旧 baseline_results.csv；把 outputs 组织为 outputs/ICP/Lx 结构；新增 algorithms/pipelines/utils、L2/L3 结果 JSON、L2 动画帧与 mp4、quarantine 下的 global_registration/icp_multistart 与旧 playbook_l2。
- 10/6 上午~13:xx（未提交工作区）：L3 数据与复现（data/L3、L3_new，L3_probe/reproduction/repro_seeds/3 npy，l3_svd_icp_pipeline.py）、L2 动画帧 031~079 重跑、preview 探索（_gen_preview.py、_coarse_sim.npy）、_tmp 临时文件、docs v1.4 参赛方案 / 项目说明 v1.2 / playbook_v1.0 / status.md。
