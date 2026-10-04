# agent-pointcloud-registration
Agent驱动点云自动配准系统｜2026江苏省AI+科学与工程黑客松

Open3D、numpy、matplotlib


传统点云配准高度依赖人工根据点云质量选择算法、调试参数，在高噪声、低重叠等复杂场景下极易配准失败，需要人工反复试参排查。本项目基于 AGH 智能体构建全自动点云配准系统：通过感知模块提取点云特征，由大模型智能体自主决策配准策略，调用 Open3D 工具链执行 RANSAC 粗配准与 ICP 精配准；配准完成后自动评估结果，若配准失败则诊断原因并更换策略重试，实现无人工干预的闭环配准。实验表明，相比固定参数流水线，本智能体方案在困难场景下可显著提升配准成功率。

## 本地库结构

agent-pointcloud-registration\
├── README.md            ← 门面+交接文档：项目简介、环境配置、怎么跑
├── requirements.txt     ← 依赖清单
├── .gitignore           ← 排除 __pycache__\、*.pyc 这类垃圾文件
├── register_minimal.py  ← demo，留作纪念和回归测试
├── src\                 ← 正式代码都进这里
│   ├── make_data.py     ← 数据生成器（造四关卡点云）
│   ├── evaluate.py      ← 评测函数（算旋转/平移误差）
│   └── run_baseline.py  ← 朴素ICP基线（产出"失败表"）
├── configs\             ← 四关卡的参数配置（L1-L4各一份）
├── outputs\             ← 图、结果表、运行日志（证据仓库）
├── tests\               ← 测试样例：正常/边界/失败三类（官网硬性提交项）
└── docs\                ← 方案、任务书、开发日志、架构图、排坑记录等


