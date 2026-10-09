# DEV-X Headless AGH Smoke

这是一个只读的开发级 Smoke Task。请由 Agnes 在 AGH 中完成以下任务：

1. 读取当前 workspace 根目录的 `README.md`，以及为确认目录存在所必需的最少状态信息。
2. 返回 README 中的项目名称，并返回一个当前项目中确实存在的目录名称。
3. 明确说明你只进行了只读检查。

严格限制：

- 不运行任何 Probe。
- 不运行任何 Registration、Evaluator 或点云实验。
- 不读取任何 Ground Truth（GT）。
- 不修改任何文件。
- 不修改、移动、覆盖或删除 `outputs/submission_evidence/B3/` 下的 Frozen Evidence。
- 缺失信息写 `UNKNOWN` 或 `MISSING`，不得猜测。
