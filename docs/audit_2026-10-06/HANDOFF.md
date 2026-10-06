# HANDOFF.md（一页交接）

项目：AGH驱动的点云自动配准智能体。只读审计交接，截至 2026-10-06。

## 现在已经完成什么
- 环境：AGH 本地服务 + conda pointcloud_agh (Python 3.11, Open3D 0.20.0) 已通。
- 数据生成器 make_data（噪声/离群/裁剪可控，固定 seed 可复现）。
- 评测尺子 evaluate（旋转/平移误差、fitness、内置自测通过）。
- 四关朴素 ICP 基线 + 量化表 baseline_results.csv（L1 PASS，L2/L3/L4 FAIL，故事线成立）。
- L2 大角度：FPFH+RANSAC+ICP、SVD全局初值+ICP 两条路线均能从失败救到达标；闭环调度器(closed_loop_l2)有结构化报告；配准动画(80帧+mp4)。
- L3 脏数据：seed303 用鲁棒 FPFH+RANSAC 可救到达标；已做 3 seed 复现(seed505/707 失败，暴露对称/翻转解)。
- 文档：参赛方案 v1.4、项目说明 v1.2、playbook v1.0、工作流程总结、status。
- Git 4 提交，GitHub 远程同步。

## 现在还没完成什么
- “AGH 模型自主决策”无任何落盘证据（无 decision trace / 工具调用链 / 模型参与记录）——核心主张与现状的最大断层。
- L3 未稳定达标（仅 seed303 成功）；playbook 推荐策略与实际成功策略不一致。
- L4 仅基线失败，无补救/成功实验。
- L1 缺“识别简单场景、避免重型算法”的论证证据。
- 多 seed 复跑、角度/噪声/裁剪扫描、三组消融、参数自适应、点云诊断器、G-ICP、held-out 组合 case：均无运行证据。
- 正式 3–5 分钟演示视频未做；L2 帧/动画在提交后重跑过、未定稿；README 与当前仓库不一致。

## 哪些结果最可信
- 强证据（有输出+指标+可对应脚本/日志）：
  - outputs/reports/baseline_results.csv（四关基线）
  - outputs/ICP/L2/l2_global_registration_result.json、l2_closed_loop_result.json（L2 对照与闭环）
  - outputs/L2/l2_registration_result.json + l2_registration_log.txt（L2 SVD+ICP，含 timestamp）
  - outputs/L3_probe_existing_seed303.json、L3_reproduction_summary.json + 3 npy（L3 探测与复现）
  - outputs/L2/visuals/l2_registration_animation.mp4（L2 动画）
  - outputs/reports/evaluate_test.txt（评测自检）

## 当前最重要的 3 个缺口
1. 无 AGH/Agnes 模型参与配准决策的证据（decision trace / 工具调用链 / 模型记录）——提交硬约束“运行证据”缺核心。
2. L3 稳定性不足（seed505/707 失败）且 playbook 与实际策略不一致。
3. 缺正式演示视频与 L2/L3 多 seed 复跑定稿；L4 无补救实验。

## 下一次 AGH 会话首先应读哪些文件
1. docs/audit_2026-10-06/PROJECT_AUDIT.md（全局事实与能力边界）
2. docs/audit_2026-10-06/EXPERIMENT_LEDGER.md（实验台账，哪些有强证据）
3. docs/audit_2026-10-06/OPEN_QUESTIONS.md（需你本人拍板的 11 个问题）
4. docs/AGH驱动的点云自动配准智能体_参赛方案_v1.4.md（目标与排期）
5. configs/L1~L4.yaml（当前关卡定义的事实基准）

规则提醒：不修改源码/配置，不重跑补证据；区分 A代码存在 / B疑似运行 / C已证运行 / D有量化结果。
