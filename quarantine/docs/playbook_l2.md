# L2 场景点云配准诊断决策手册

> 适用范围：L2 场景（大角度旋转 60°~80° 区间 × 3 轴 + 干净数据：无噪声、无离群点、无裁剪）。
> 达标阈值：旋转误差 < 5° 且 fitness > 0.8（`configs/L2.yaml` → `thresholds`）。
> 本手册所有数值均来自实测（seed_202/303/404，配置同 `configs/L2.yaml` 的 L2 参数，种子不同），非拍脑袋设定。

## 诊断决策表

| 指标模式 | 失败类型诊断 | 对应配准策略 |
|---|---|---|
| fitness < 0.3，旋转误差 > 120°（远大于 5° 阈值），rmse < 0.03（很小），数据无噪声/无离群点 | 初始位姿偏差过大：单位阵初值与真实大角度变换差距远超 ICP 局部收敛域，点到面 ICP 收敛到局部极小（只拟合少量近匹配点，rmse 小但 fitness 极低） | `src/algorithms/global_registration.py`：FPFH 特征提取 + RANSAC 全局粗配准（`registration_ransac_based_on_feature_matching`）+ 点到面 ICP 精化 |
| fitness ≥ 0.8 且 旋转误差 < 5° | 无失败（已达标），无需额外处理 | 直接保留当前变换结果，无需切换策略 |

## 实测阈值参考（引用实测真实数值）

- **朴素 ICP（单位阵初值）在 L2 场景下的稳定失败特征**（3 个种子实测）：
  - rot_err ≈ 125°~135°（seed_202: 125.40°, seed_303: 135.29°, seed_404: 125.63°）
  - fitness ≈ 0.11~0.14（seed_202: 0.134, seed_303: 0.139, seed_404: 0.111）
  - rmse ≈ 0.022~0.023（远小于 0.03，说明是"局部拟合了少量点"而非完全没匹配到点）
  - 结论：**只要看到"rmse 小 + fitness 极低 + 旋转误差大"这一组合特征，即可判定为"初始位姿偏差过大"，无需额外噪声/离群点诊断（L2 数据本身干净）**。
- **FPFH+RANSAC+ICP 达标特征**（3 个种子实测）：
  - rot_err ≈ 0.0°，trans_err ≈ 0.0（浮点误差量级 ~1e-16）
  - fitness = 1.0，rmse ~1e-16
  - 耗时 ≈ 0.4~0.6s

## 使用方式

1. 对目标 L2 数据先跑 `src/algorithms/icp_naive.py`（基线初测，单位阵初值）。
2. 按决策表对照实测指标：若命中"初始位姿偏差过大"特征 → 切换调用 `src/algorithms/global_registration.py`。
3. 用 `src/evaluate.py` 的 `evaluate_case` 对 `global_registration` 输出的变换矩阵复核达标情况（旋转<5° 且 fitness>0.8）。
