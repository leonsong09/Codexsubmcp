# CodexSubMcp Cleanup Redesign Design

## Goal

把 CodexSubMcp 从“只清理 orphan MCP suite 的 GUI 工具”升级为“围绕 Codex 当前态、重复 MCP 泄漏、预览式清理、历史审计”的单一主流程工具。

核心要解决两个问题：

1. 准确展示当前状态：
   - 运行中的子代理数量
   - 运行中的 suite 数量
   - 运行中的 MCP 实例数量
   - 已配置 MCP 数量
2. 解决核心泄漏：
   - 子代理已结束或 MCP 已重复拉起后，旧的 nodejs / cmd / npx / uvx 链仍然挂在 live Codex 进程下，占用内存

## Background

现有项目对 cleanup 的建模以 `orphaned_after_codex_exit` 为中心，只有 Codex 父进程不存在时才会进入清理目标。实际现场证据表明，核心问题不仅是 orphan suite，还包括：

- `attached_to_live_codex` 下同一种 MCP 被重复启动多轮
- 旧启动批次未退出
- 现有 GUI 虽然有“总览 / 清理 / MCP 检索 / 日志”，但逻辑层次混杂：
  - 当前态观测
  - 清理目标判定
  - MCP 配置扫描
  - 历史回放
  混在多个页面里，没有统一主流程

同时，当前 MCP 扫描模型主要面向 JSON 配置和 npm global 候选，对 Codex CLI 不准确。Codex 源码与本机验证表明：

- 全局 MCP 主配置位于 `~/.codex/config.toml`
- 还可能存在项目级 `.codex/config.toml`
- 本机当前运行中的 MCP 类型与 `~/.codex/config.toml` 中配置类型一致
- `installed_candidates` 对当前问题排查价值低，应移除

## Product Flow

产品只保留一条主流程：

**刷新 → 分析 → 预览 → 清理 → 日志**

约束：

- 没有独立的“扫描 MCP”流程；MCP 扫描并入“刷新”
- 没有基于旧快照直接清理的入口
- 清理只能消费最近一次 preview 结果
- 日志不反推当前状态；当前状态只来自最近一次 refresh 生成的数据

## Data Sources

### 1. Codex 配置

只读取两类配置来源：

1. 全局配置：`~/.codex/config.toml`
2. 项目配置：从当前仓库向上查找 `.codex/config.toml`

不再读取：

- Claude JSON 配置
- Cursor JSON 配置
- 旧 `Codex/mcp.json`
- installed candidates

### 2. Codex 子代理状态

读取 `~/.codex/state_5.sqlite` 中 `thread_spawn_edges.status = 'open'` 的数量，作为“运行中的子代理数量”。

### 3. Windows 进程快照

继续使用当前 Win32 进程快照方式，作为：

- suite 构建基础
- 运行中 MCP 实例基础
- stale attached branch 判定基础

## Architecture

### Layer 1: Snapshot

`SystemSnapshot` 负责采集当前原始状态，不做清理判定。

```python
SystemSnapshot = {
  "snapshot_id": str,
  "captured_at": str,
  "codex": {
    "global_config_path": str | None,
    "project_config_path": str | None,
    "open_subagent_count": int,
  },
  "configured_mcps": list[ConfiguredMcp],
  "processes": list[ProcessInfoPayload],
}
```

### Layer 2: Analysis

`AnalysisResult` 从 `SystemSnapshot` 计算：

- 已配置 MCP
- 正在运行的 MCP 类型和实例数
- drift
- live suites
- orphan suites
- stale attached branches

```python
AnalysisResult = {
  "snapshot_id": str,
  "analyzed_at": str,
  "summary": {...},
  "running_mcps": [...],
  "drift": {...},
  "live_suites": [...],
  "orphan_suites": [...],
  "stale_attached_branches": [...],
}
```

### Layer 3: Preview

`CleanupPreview` 只表达“本次若执行清理，会清什么”。

```python
CleanupPreview = {
  "snapshot_id": str,
  "previewed_at": str,
  "summary": {...},
  "targets": [...],
}
```

### Layer 4: Execution

`CleanupResult` 只表达“执行后实际发生了什么”。

```python
CleanupResult = {
  "snapshot_id": str,
  "preview_id": str | None,
  "executed_at": str,
  "summary": {...},
  "actions": [...],
  "error": str | None,
  "post_refresh_snapshot_id": str | None,
}
```

### Layer 5: Lifetime Stats

`LifetimeStats` 表达历史累计清理成果，只从成功的 cleanup 日志汇总，不从 refresh / preview 汇总。

```python
LifetimeStats = {
  "total_refresh_count": int,
  "total_preview_count": int,
  "total_cleanup_count": int,
  "total_closed_suite_count": int,
  "total_closed_stale_branch_count": int,
  "total_killed_mcp_instance_count": int,
  "total_killed_process_count": int,
  "last_cleanup_at": str | None,
}
```

## MCP Scanning Model

### Configured MCP

从 Codex TOML 中读取：

- `mcp_servers.<name>`
- `type`
- `command`
- `args`
- `url`
- `env`
- `cwd`
- `startup_timeout_ms`
- `startup_timeout_sec`
- `tool_timeout_sec`

统一归一化后输出：

- `name`
- `source` (`codex_global_config` / `codex_project_config`)
- `type`
- `command`
- `args`
- `env_keys`
- `startup_timeout_ms`
- `tool_timeout_sec`

### Running MCP

从进程快照中归一化出 `tool_signature`，首批支持：

- `ace-tool`
- `agentation-mcp`
- `server-memory`
- `server-sequential-thinking`
- `mcp-server-fetch`
- `playwright-mcp`
- `chrome-devtools-mcp`

### Drift

基于 `configured_mcps` 与 `running_mcps` 的 `tool_signature` 集合计算：

- `configured_not_running`
- `running_not_configured`

## Cleanup Model

### Existing target: orphan suite

保留现有逻辑：

- Codex 父进程已退出
- 整个 orphan suite 作为清理目标

### New target: stale attached branch

这是本次设计的核心。

#### Attached branch 定义

对每个 `attached_to_live_codex` suite：

- 找到所有 `ppid == live_codex_pid` 的 direct launchers
- 每个 direct launcher 及其所有后代构成一个 `launcher_branch`

#### tool_signature 归一化

每个 branch 根据 launcher command line 归一化为 `tool_signature`。

#### stale 判定

在同一 `live_codex_pid` 内：

- 按 `tool_signature` 分组
- 如果某组只有 1 个 branch，则不处理
- 如果某组有多个 branch：
  - 保留最新 branch
  - 更老 branches 全部标记为 stale

#### 安全边界

- 只清理 stale 分支，不清整套 live suite
- 每种工具始终保留最新 branch
- 必须先 refresh，再 preview，再 cleanup
- cleanup 只允许基于最近一次 preview 结果

## Execution Strategy

### orphan suite

保持现有行为：

- 对 orphan suite root 执行递归终止

### stale attached branch

对 stale branch 的 launcher root 执行递归终止：

- `cmd.exe /c npx ...`
- `uvx.exe ...`
- `ace-tool.cmd ...`

执行方式保持 Windows 递归 kill 风格，确保清理 launcher 及其后代，而不是只杀 leaf node。

## Logging

统一三类日志：

### refresh log

记录快照摘要与来源状态。

### preview log

记录本次预览目标与预计清理规模。

### cleanup log

记录本次实际清理结果。只有：

- `kind == cleanup`
- `summary.success == true`

才纳入累计统计。

### File naming

- `refresh-YYYYMMDD-HHMMSS.json`
- `preview-YYYYMMDD-HHMMSS.json`
- `cleanup-YYYYMMDD-HHMMSS.json`

## GUI Responsibilities

### Overview Page

只负责：

- 当前态摘要
- 最近一次结果摘要
- 累计清理摘要
- 主操作按钮（刷新 / 预览 / 清理）

不负责：

- 原始 MCP 明细
- 清理目标表
- 历史日志详情

### MCP Page

只负责“诊断”：

- 已配置 MCP
- 正在运行 MCP
- drift

不负责：

- 清理执行
- 历史回放

### Cleanup Page

只负责“本次工作台”：

- 当前 preview 摘要
- orphan suite targets
- stale attached branch targets
- 目标详情、风险提示、进程树

### Log Page

只负责“历史回放”：

- refresh / preview / cleanup 摘要列表
- 详情 JSON
- 错误信息

## Testing Strategy

### Confirmed feasibility spike

已通过最小 spike 证明 stale attached branch 判定可行：

- `tests/test_attached_cleanup.py`
- `codexsubmcp/core/stale_attached.py`

相关验证：

- `pytest tests/test_attached_cleanup.py`
- `pytest tests/test_core_cleanup.py tests/test_cleanup_codex_mcp_orphans.py tests/test_attached_cleanup.py`

### Remaining tests to add

1. `tests/test_codex_mcp_config.py`
   - 全局 TOML
   - 项目 `.codex/config.toml`
   - 字段提取

2. `tests/test_system_snapshot.py`
   - 快照对象拼装
   - open subagent count 注入

3. `tests/test_analysis.py`
   - running MCP
   - drift
   - stale attached branch 汇总

4. `tests/test_cleanup_preview.py`
   - orphan + stale target 合并

5. `tests/test_cleanup_execution.py`
   - stale branch 递归 kill
   - cleanup result 统计

6. `tests/test_runtime_logs.py`
   - 三类日志
   - lifetime stats 汇总

7. GUI smoke / behavior tests
   - Overview
   - MCP page
   - Cleanup page
   - Log page

## Implementation Phases

### Phase A

- Codex TOML 读取
- `SystemSnapshot`
- `AnalysisResult`
- stale attached branch 分析接入

### Phase B

- `CleanupPreview`
- `CleanupResult`
- runtime logs
- `LifetimeStats`

### Phase C

- GUI 改造：
  - 总览页
  - MCP 页
  - 清理页
  - 日志页

## Out of Scope

本轮不做：

- 多产品兼容 MCP 扫描（Claude / Cursor）
- installed candidates 展示
- 自动后台清理策略重写
- 远程 Codex / 非 Windows 平台适配

## Risks

1. stale branch 误杀风险
   - 通过“每种 tool_signature 保留最新 branch”降低风险
2. 项目级 `.codex/config.toml` 搜索边界不清
   - 先按当前工作目录向上查找实现
3. 日志过多时累计统计变慢
   - 首版从 cleanup logs 汇总，后续再视情况加缓存

## Acceptance Criteria

1. 刷新后，用户能一眼看到：
   - 运行中子代理数
   - 运行中 suite 数
   - 运行中 MCP 实例数
   - 已配置 MCP 数
2. MCP 页只展示：
   - configured
   - running
   - drift
3. 清理页能同时展示：
   - orphan suite targets
   - stale attached branch targets
4. cleanup 不再只处理 orphan，还能处理 stale attached branch
5. 日志能区分 refresh / preview / cleanup
6. 总览能显示累计清理统计
