# Headless AGH Workflow

## 结论与边界

本机当前 AGH 支持非交互任务：`agh -p --mode json` 通过 AGH backend 创建 session、调用所选 Agnes 模型、执行经 AGH 管理的工具，并在 stdout 输出一个 `agnes-cli-result/v1` 结果行。Codex 和本地脚本只负责准备 Prompt、启动 AGH、归档真实输出；不能替代 Agnes 作 Probe、registration method、parameter policy 或 `ACCEPT` / `RETRY` / `ABORT` 决策。

## 当前本机入口

源码仓库：`D:\STUDY\darker\agnes-harness`

当前已构建 CLI 的入口位于：

```text
D:\STUDY\darker\agnes-harness\packages\cli\dist\<最新 local 构建>\agnes.mjs
```

DEV-X 验证时实际选中的构建是 `local-dev-20261007-234020144\agnes.mjs`；CLI 自报 `agh 0.0.0 node 24.21.0 protocol _agnes/v1`。

从源码构建当前 CLI：

```powershell
pnpm --filter @agnes/cli build:local
```

启动包含 daemon/backend 和 Web UI 的 App Server（默认可使用 4177；本机开发惯例可改为 4180）：

```powershell
node <agnes.mjs> serve --profile local-dev --cwd D:\STUDY\darker\agent-pointcloud-registration --port 4180
```

普通 CLI 不要求先打开网页；它连接同一 AGH_HOME/profile 下已运行的 daemon，或按 CLI 生命周期启动 backend。Web 与 CLI 只有在 `AGH_HOME`、profile 和 data directory 相同时才共享后台与 session。`--standalone`/临时 `AGH_HOME` 会形成隔离后台，不应被误称为网页中的同一 session。

## 运行文件化 Task

Prompt 放在项目 `tasks/`。不要把正式 Prompt 硬编码到 PowerShell。示例：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\agh_run.ps1 `
  -PromptFile tasks\DEVX_SMOKE.md `
  -RunLabel DEVX_SMOKE
```

launcher 将 workspace 固定为脚本所在项目根目录，并通过 stdin 把 Prompt 交给 AGH：

```text
D:\STUDY\darker\agent-pointcloud-registration
```

默认使用 `local-dev` profile 中已经选择的 account/model。需要显式覆盖时，按当前 CLI 语法传入完整映射，例如：

```powershell
-Model "main=<route>/<model>"
```

本次 profile 中已有且实际调用的默认模型是 `agnes-3.0-flash`（Agnes 3.0 Flash）。模型选择来自 AGH 配置与 session 的 `modelSettings`；launcher 不持有模型凭据，也不直接调用模型 API。

当前 CLI 没有通用的 `--permission` 参数。permission/approval 来自 profile 与 session；本机 `local-dev` 快照为 `approvals.mode = manual`。launcher 的 `-PermissionMode profile-default` 只记录真实状态，不模拟授权，也不启用 `/yolo`。如果未来 CLI 增加官方 permission 参数，应先按当时 `--help` 与源码更新 launcher。

这是正式 tool-bearing Run 的当前能力边界：`packages/cli/src/modes/print.ts` 没有为 print session 注册 permission handler；SDK 对无人处理的 `session/request_permission` 采用默认拒绝。因而 headless 基础链路已经验证，但只有 `resolvedPolicy.requiresApproval = never` 的工具可以确认无人值守执行。DEV-X Smoke 的 `read` 与 `ls` 都满足该条件，不能由此推断 Registration 工具也满足。正式 C/D/E 前必须先只读核对目标工具的 resolved policy；若会请求 approval，当前 CLI 的最小接入方式是在 `packages/cli/src/args.ts` 增加显式 permission 参数，并在 `packages/cli/src/modes/print.ts` 创建/加载 session 后、发送 Prompt 前，通过 SDK 的 `Session.setYolo(true)` 实现用户明确选择的 full 模式，或注册一个有明确、可审计判定策略的 `onPermissionRequest` handler。不得在 launcher 外层伪造批准或绕过 AGH。

## Evidence

每次运行写入：

```text
outputs/development/headless_agh/<run_label>_<timestamp>/
```

核心文件：

- `invocation.json`：入口、workspace、profile、参数和 Prompt 传输方式。
- `prompt_snapshot.md`：实际提交的 Prompt 快照。
- `stdout.log`、`stderr.log`：AGH 进程原始输出。
- `exit_status.json`：进程退出码、AGH 结果退出码、reason 和 session id。
- `agh_identifiers.json`：真实 identifier；当前 CLI 返回 session id，未提供的 task/run id 写 `NOT_AVAILABLE`。
- `environment.json`：Node、CLI、入口哈希、workspace 与 permission 口径。
- `agh_session_export.jsonl`：若成功取得 session id，则由 `agh export --format agnes` 产生的 AGH 原生事件/session 账本（保持默认脱敏，不使用 `--raw`）。
- `agh_native_records.json`：原生导出是否可得；不可得时明确为 `NOT_AVAILABLE`。

`stdout.log` 在 JSON 模式主要包含最终 `agnes-cli-result/v1`；逐项工具事件不应从 stdout 猜测，应该以 AGH 原生 session export 为准。stderr 只保存 AGH/transport/CLI 实际诊断，不将 Codex 文本包装成 AGH trace。

当前版本的 stdout JSON 可提供 `sessionId`、`reason`、`exitCode`、`lastSeq`、credits 和最终 text。stderr 可提供启动错误、notice 和 transport/CLI 诊断；JSON print 模式不承诺把每个 tool event 打到 stderr。当前 CLI 没有另外返回 task id 或 run id，因此这两项记录为 `NOT_AVAILABLE`，不可用本地 Evidence 目录名冒充。

## 如何确认 AGH 是底座

一个 Run 至少应同时满足：

1. invocation 的 executable 是当前 AGH `agnes.mjs`，并使用 `-p --mode json`。
2. workspace 是项目根目录。
3. stdout 中存在 `v = agnes-cli-result/v1` 和非伪造的 `sessionId`。
4. exit status 与 stdout 的 AGH 结果一致。
5. 能导出时，`agh_session_export.jsonl` 含该 session 的 AGH 原生事件；不能导出则必须标 `NOT_AVAILABLE`，不得补造。
6. 模型回答和工具 Observation 来自 AGH session，而不是 Codex 代答。

## Transport 与完成判定

优先以 AGH 结果行的 `reason`、`exitCode`、`sessionId` 和 `turn/end` 对应的原生账本为准。CLI 进程退出码 `0` 表示完成；`1` 表示失败；`2` 表示参数或启动错误；`3` 表示 parked；`4` 表示预算/阻塞；`5` 表示达到步骤上限。只有网络或 Web transport 报错、但已有 `turn/end` 和成功结果行时，才可判定核心 task 已完成；仅有网页断连、daemon discovery 或部分 stdout 不能证明完成。必要时运行：

```powershell
node <agnes.mjs> sessions show <session-id> --profile local-dev
node <agnes.mjs> export <session-id> --format agnes --out <path> --profile local-dev
```

## 正式 C/D/E Run 复用

为每个正式 Run 建立独立 Prompt 文件，先冻结 Prompt 和输入引用，再用相同 launcher 启动。正式比赛中的任务组织、模型决策、Probe/Registration 工具调用和 Observation 反馈必须留在 AGH/Agnes session 中；Codex 可以维护 launcher、检查配置、统计和归档 Evidence，但不能替 Agnes 作专业决策。正式输出按项目规则进入 `outputs/submission_evidence/` 的 Level → Run → Attempt 结构；本 launcher 默认的 `outputs/development/` 仅用于开发验证，正式迁移前应由正式流程显式指定合规输出根目录。

正式 Agent 阶段禁止读取 GT；Agent 停止后才允许 Independent Evaluator 读取。Frozen Evidence 始终只读。

## 本次开发环境的 ACL 注意事项

当前 AGH 版本要求 AGH_HOME、credential 父目录和 credential 文件具有 Windows 私有 DACL。Codex 沙箱会给常规 `C:\Users\GAOJUN\.agh` 加入只读沙箱 ACE，因此在本次自动化验证中使用了独立、私有的临时 AGH_HOME 镜像；只复制既有 profile 与对应 credential，不读取或输出密钥。该临时后台与常规 Web session 不共享。用户在普通 Windows 终端运行时应使用正常 AGH_HOME；若仍报告 `The credential store is unavailable.`，应先用当前 AGH 的 credential/ACL 维护流程修复权限，而不是关闭安全校验。
