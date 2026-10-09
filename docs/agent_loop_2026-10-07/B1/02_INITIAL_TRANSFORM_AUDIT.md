# 02_INITIAL_TRANSFORM_AUDIT — initial_transform_available 语义审计

**Phase B1 — 只读审计。**

---

## B1. 这个字段在哪里生成

**位置**：`src/agent_diagnose.py`，第 82 行：

```python
out = {
    ...
    "initial_transform_available": True,   # ← 硬编码为 True，永远不变
    ...
}
```

`diagnose()` 函数里，这个字段**没有任何条件判断**，始终是字面量 `True`。
不存在"检查是否有外部提供初始变换"的逻辑。

该字段随后被写入 `diagnosis.json`，并在 `agent_runner.py` 第 157 行
被复制到 `input_summary.json`（`"initial_transform_available": diagnosis["initial_transform_available"]`）。

---

## B2. `True` 的准确含义

**准确含义：系统里始终有一个 4×4 单位矩阵（identity matrix）可以作为"初始变换"使用。**

具体来源：
- `LOCAL_ICP`：`agent_tools.py` 第 93 行，`registration_icp(source, target, max_corr, np.eye(4), ...)` —
  初值固定为 `np.eye(4)`，无需外部提供，因此"永远可用"。
- `GLOBAL_FPFH_RANSAC_ICP`：`agent_tools.py` 第 151 行，RANSAC 结果作为 ICP 初值，
  该初值来自特征匹配，不是单位阵；但 RANSAC 在极个别失败时理论上可退化为 identity。

所以 `initial_transform_available = True` 的真实语义是：
> "LOCAL_ICP 工具永远可以用单位阵做初值，不需要外部先验。"

它**不反映**任何外部提供的初始变换，
也**不反映**任何上一步算法结果，
更**不涉及** Ground Truth。

---

## B3. 所谓 initial transform 是什么

**Identity matrix（单位阵）**。

- 不是配置提供（无配置文件写入此字段）
- 不是外部先验
- 不是上一步算法结果
- 不是 Ground Truth
- 是 `LOCAL_ICP` 工具写死在调用里的 `np.eye(4)`

---

## B4. Agnes 是否能看到完整 transform 矩阵

**Agnes 只能看到 `initial_transform_available: true/false` 这个布尔值**，
看不到 identity 矩阵本身，也看不到任何其他变换矩阵。

`diagnosis.json` 里的字段是布尔 `True`，
`input_summary.json` 里的字段也是布尔值，
没有任何矩阵数据被传入 Agnes 的决策上下文。

---

## B5. 这个信息是否影响算法选择

**目前不影响，因为当前 Python 代码里也没有读这个字段来分支。**

`agnnes_decide` 函数（`agent_runner.py` 第 35-90 行）
只读 `base_scale`、`centroid_distance`、`density_ratio` 三个字段，
`initial_transform_available` 完全被忽略。

在未来若 Agnes 是真实 LLM，此字段可能会影响决策
（"有初始变换 → LOCAL_ICP 可用"），
但当前没有这种逻辑路径。

---

## B6. 是否存在 GT 泄露风险

**不存在 GT 泄露。**

`initial_transform_available = True` 与 `gt_transform.npy` 没有任何关系。
它是工具内部固定行为（`np.eye(4)` 初值），不是从 GT 文件派生。

GT 文件只在 `agent_evaluator.py` 的 `evaluate_agent_result` 里被读取，
而该函数在 Agent 循环结束后才被调用，时序正确。

---

## 字段命名建议（只分析，不修改）

**字段名 `initial_transform_available` 存在语义误导风险：**

1. **含义过宽**：字面上读起来像是"有一个外部提供的初始变换可用"，
   容易让 Agnes（LLM）或未来开发者误以为是"某个上游算法给出的变换初值"。

2. **真实含义过窄**：实际只是"LOCAL_ICP 可以用 identity 阵做初值"，
   这是工具固有属性，与输入数据完全无关，永远是 `True`。

3. **对 Agent 决策无信息量**：既然它永远是 `True`，
   出现在诊断 JSON 里只是噪音，
   可能让 Agnes 误认为"已经有比较好的初值，可以直接用 LOCAL_ICP"，
   与 hard branch 的实际意图（offset 大要用 GLOBAL）产生矛盾。

**建议**（B2 实施时考虑，本 B1 不修改）：
- 若保留此字段，改名为 `unit_matrix_init_available`（更精确），并加注释说明语义；
- 或者直接在诊断里删掉这个字段，因为它是工具固有属性而非数据属性；
- 若未来有"外部提供初始变换"的功能，再用一个不同字段表达。

---

## 结论

**GT_LEAKAGE: PASS**
（此字段与 GT 文件无任何关联，时序上 Evaluator 也在 Agent 停止后才读 GT。）

**字段语义：误导风险中等，建议 B2 重新命名或移除。**

---

## 证据路径

| 项目 | 位置 | 行号 |
|---|---|---|
| 字段生成（硬编码 True） | `src/agent_diagnose.py` | 82 |
| 字段写入 diagnosis.json | `src/agent_diagnose.py` | 82（在 out dict 里） |
| 字段复制进 input_summary | `src/agent_runner.py` | 157 |
| LOCAL_ICP 用 np.eye(4) | `src/agent_tools.py` | 93 |
| Global ICP 初值来自 RANSAC | `src/agent_tools.py` | 151 |
| GT 文件读取（仅 Evaluator） | `src/agent_evaluator.py` | 38（T_gt = load_transform） |
