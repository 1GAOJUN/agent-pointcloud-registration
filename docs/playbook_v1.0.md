# 点云配准诊断决策总手册 v1.0

> 适用范围：L2（大角度旋转 + 干净数据）与 L3（中等角度旋转 + 高斯噪声 + 离群点）两类场景。
> 达标阈值：旋转误差 < 5° 且 fitness > 0.8。
> 本手册所有数值均来自实测（L2：seed_202/303/404；L3：seed_303），非拍脑袋设定。

## 诊断决策表

| 指标模式 | 失败类型诊断 | 对应配准策略 |
|---|---|---|
| **L2型**：rot_err > 120°（远大于5°阈值），fitness < 0.3，rmse < 0.03（很小），数据无噪声/无离群点（source/target 点数相同） | 初始位姿偏差过大：大角度旋转（真值~125°）使单位阵初值远超 ICP 局部收敛域，点到面 ICP 只拟合少量局部近匹配点（rmse 小但 fitness 极低），收敛到局部极小 | `src/algorithms/global_registration.py`：FPFH 特征提取 + RANSAC 全局粗配准 + 点到面 ICP 精化（参数为 L2 干净数据调优版） |
| **L3型**：rot_err 处于 25°~40° 区间（中等，非 L2 型极端大角度），fitness 在 0.2~0.4 之间（高于 L2 型失败特征的低 fitness，但达不到 0.8），rmse < 0.03，且 target 点数明显多于 source（脏数据信号） | 中等角度旋转 + 脏数据（离群点/噪声）双因素叠加：ICP 局部优化被离群点拉偏，且初值与真值的角度差距中等但超过单次 ICP 收敛域；单纯剔除离群点（`icp_robust_outlier.py`）不足以跨越角度差，FPFH+RANSAC（`global_registration_robust.py`，放宽匹配距离阈值）在近似对称几何 + 脏数据下会误判对称翻转解（ransac_fitness=1.0 但 ransac_rmse 偏大~0.09，rot_err 反而恶化到 ~160°） | `src/algorithms/icp_multistart.py`：固化的离散 Z 轴预旋转初值（0/90/180/270°）+ 统计离群点剔除 + 点到面 ICP，取 ICP fitness 最高者作为最终结果 |

## 实测阈值参考（引用真实数值）

### L2 场景（干净数据、大角度旋转 ~125°，seed_202/303/404）

- **朴素 ICP（单位阵初值）稳定失败特征**：
  - rot_err：125.40°（seed_202）、135.29°（seed_303）、125.63°（seed_404）
  - fitness：0.134、0.139、0.111
  - rmse：~0.022~0.023（远小于 0.03，说明只拟合到少量局部近匹配点，而非完全没匹配）
- **FPFH+RANSAC+ICP 达标特征**：
  - rot_err ≈ 0.0°，trans_err ≈ 0.0（浮点误差量级 ~1e-17）
  - fitness = 1.0，rmse ~1e-16
  - 耗时 ≈ 0.4~0.6s

### L3 场景（脏数据、中等角度旋转 ~50°，seed_303）

- **朴素 ICP（单位阵初值）失败特征**：
  - rot_err = 30.64°，fitness = 0.323，rmse = 0.0254
- **单纯剔除离群点 + 单位阵初值 ICP（`icp_robust_outlier.py`）失败特征**：
  - rot_err = 29.37°，fitness = 0.199（比朴素 ICP 更低，说明剔除离群点后数据更"干净"但初值角度差问题没有解决）
- **FPFH+RANSAC（L3 专用参数，`global_registration_robust.py`）失败特征**：
  - rot_err = 160.35°（比初测还差），fitness = 0.782（略低于 0.8 达标线）
  - ransac_fitness = 1.0 但 ransac_rmse = 0.09（脏数据下 RANSAC 把"错误但自洽"的对称翻转解误判为最优内点集）
- **多初值 ICP（`icp_multistart.py`）达标特征**：
  - rot_err = 0.106°，trans_err = 0.00016
  - fitness = 1.0，rmse = 0.0049
  - 耗时 ≈ 14.76s

## 策略选择要点（非步骤流程，供诊断时快速对照）

- 看到"rot_err 极大（>100°）+ fitness 极低（<0.2）+ rmse 小 + 数据干净" → L2 型，用 `global_registration.py`。
- 看到"rot_err 中等（25°~40°）+ fitness 中间（0.2~0.4）+ 数据脏（target 点数 > source）" → L3 型，用 `icp_multistart.py`；**不推荐**继续调 FPFH+RANSAC 参数（脏数据 + 近似对称几何下容易陷入对称翻转误解）。
