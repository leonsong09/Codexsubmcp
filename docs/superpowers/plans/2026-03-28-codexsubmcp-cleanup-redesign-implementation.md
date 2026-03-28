# CodexSubMcp Cleanup Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 CodexSubMcp 以“刷新 → 分析 → 预览 → 清理 → 日志”为唯一主流程，准确展示当前运行态，并能清理 live Codex 会话下重复堆积的 stale MCP branches。

**Architecture:** 先把 Codex TOML 配置、SQLite open 子代理状态、Windows 进程快照统一收敛成 `SystemSnapshot`，再通过 `AnalysisResult` / `CleanupPreview` / `CleanupResult` / `LifetimeStats` 建立稳定的业务层。GUI 只消费这些结果对象，不自行推导业务逻辑；日志层统一记录 refresh / preview / cleanup 三类事件并从成功 cleanup 汇总累计统计。

**Tech Stack:** Python 3.12, PySide6, argparse, sqlite3/tomllib, subprocess, dataclasses, pathlib, json, pytest, pytest-qt

---

## Planned File Map

### Core — Configuration and Snapshot

- Create: `codexsubmcp/core/codex_mcp_config.py`
  - 读取 `~/.codex/config.toml` 与项目 `.codex/config.toml`
  - 归一化 `mcp_servers` 字段
- Create: `codexsubmcp/core/system_snapshot.py`
  - 组装 `SystemSnapshot`
  - 采集 configured MCP、open 子代理数、Windows 进程快照
- Create: `codexsubmcp/core/analysis.py`
  - 生成 `AnalysisResult`
  - 计算 running MCP、drift、live/orphan suites、stale attached branches
- Create: `codexsubmcp/core/runtime_logs.py`
  - 写 refresh / preview / cleanup 日志
  - 从成功 cleanup 日志汇总 `LifetimeStats`
- Modify: `codexsubmcp/core/models.py`
  - 保留 `ProcessInfo / ProcessSuite / CleanupReport / McpRecord`
  - 只做必要补充；新增大对象优先拆分到新模块中
- Modify: `codexsubmcp/core/cleanup.py`
  - 从 orphan-only 模型升级为 preview / execute 双阶段
  - 支持 `orphan_suite` 与 `stale_attached_branch` targets
- Modify: `codexsubmcp/core/stale_attached.py`
  - 从最小 spike 升级到正式分析/执行输入模型

### Platform / CLI

- Modify: `codexsubmcp/cli.py`
  - `scan mcp` 改为输出 configured + running + drift
  - cleanup headless 输出升级为 preview/result 结构
- Modify: `codexsubmcp/app_paths.py`
  - 明确日志路径与计划中的 stats / cache 使用约束
- Reuse: `codexsubmcp/platform/windows/processes.py`
  - 继续提供 Win32 进程快照

### GUI

- Modify: `codexsubmcp/gui/main_window.py`
  - 收口主流程状态：最近 snapshot / analysis / preview / result / stats
  - 移除独立 `scan-mcp` GUI 工作流，改成统一 refresh 工作流
- Modify: `codexsubmcp/gui/pages/overview_page.py`
  - 只展示当前态摘要、最近结果、累计统计、主操作按钮
- Modify: `codexsubmcp/gui/pages/mcp_page.py`
  - 只展示 configured / running / drift
  - 移除 installed candidates 视图
- Modify: `codexsubmcp/gui/pages/cleanup_page.py`
  - 只展示本次 preview targets 与详情
- Modify: `codexsubmcp/gui/pages/log_page.py`
  - 展示 refresh / preview / cleanup 摘要与详情
- Optional Create: `codexsubmcp/gui/workflow_state.py`
  - 如果 `main_window.py` 状态管理开始过大，则抽出页面共享状态容器

### Tests

- Create: `tests/test_codex_mcp_config.py`
- Create: `tests/test_system_snapshot.py`
- Create: `tests/test_analysis.py`
- Create: `tests/test_cleanup_preview.py`
- Create: `tests/test_cleanup_execution.py`
- Create: `tests/test_runtime_logs.py`
- Modify: `tests/test_mcp_inventory.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_gui_smoke.py`
- Keep / Extend: `tests/test_attached_cleanup.py`
- Keep / Extend: `tests/test_core_cleanup.py`

---

### Task 1: Codex TOML 配置读取红灯测试

**Files:**
- Create: `codexsubmcp/core/codex_mcp_config.py`
- Create: `tests/test_codex_mcp_config.py`

- [x] 写失败测试：可读取 `~/.codex/config.toml` 中 `[mcp_servers]` 项并归一化出 `name/source/command/args`
- [x] 写失败测试：当前仓库向上查找 `.codex/config.toml` 时，项目级来源会被标记为 `codex_project_config`
- [x] 写失败测试：`env/startup_timeout_ms/tool_timeout_sec/type` 会落到统一输出字段中
- [x] 写失败测试：不再接受 Claude / Cursor / 旧 Codex JSON 路径作为 configured 来源
- [x] 运行红灯验证
  - Run: `pytest tests/test_codex_mcp_config.py -q`
  - Expected: FAIL，提示 TOML 读取或字段归一化能力不存在
- [x] 实现最小 TOML 读取与来源归一化
- [x] 运行转绿验证
  - Run: `pytest tests/test_codex_mcp_config.py -q`
  - Expected: PASS

### Task 2: 系统快照模型红灯测试

**Files:**
- Create: `codexsubmcp/core/system_snapshot.py`
- Create: `tests/test_system_snapshot.py`
- Modify: `codexsubmcp/app_paths.py`

- [x] 写失败测试：`build_system_snapshot()` 会组合 configured MCP、open 子代理数、进程快照
- [x] 写失败测试：当全局 / 项目配置不存在时，snapshot 仍能返回稳定空集合与路径状态
- [x] 写失败测试：snapshot 会生成 `snapshot_id` 与 `captured_at`
- [x] 运行红灯验证
  - Run: `pytest tests/test_system_snapshot.py -q`
  - Expected: FAIL，提示快照对象或 builder 不存在
- [x] 实现最小 snapshot builder
- [x] 运行转绿验证
  - Run: `pytest tests/test_system_snapshot.py -q`
  - Expected: PASS

### Task 3: 分析层红灯测试（running / drift / stale）

**Files:**
- Create: `codexsubmcp/core/analysis.py`
- Modify: `codexsubmcp/core/stale_attached.py`
- Modify: `tests/test_attached_cleanup.py`
- Create: `tests/test_analysis.py`

- [x] 写失败测试：`analyze_snapshot()` 会输出 `configured_mcp_count/running_mcp_instance_count/open_subagent_count`
- [x] 写失败测试：当 running 与 configured 完全一致时，`drift_missing_runtime_count = 0` 且 `drift_unconfigured_runtime_count = 0`
- [x] 写失败测试：当存在运行中但未配置的 MCP 时，`running_not_configured` 会命中对应 `tool_signature`
- [x] 写失败测试：stale attached branches 会在 `AnalysisResult` 中聚合为稳定条目，包含 `tool_signature/live_codex_pid/latest_kept_launcher_pid`
- [x] 写失败测试：running MCP 汇总会把多个进程实例压缩成 `tool_signature + instance_count + live_codex_pid_count`
- [x] 运行红灯验证
  - Run: `pytest tests/test_attached_cleanup.py tests/test_analysis.py -q`
  - Expected: FAIL，提示分析对象或摘要字段缺失
- [x] 只实现支撑测试通过的最小分析逻辑
- [x] 运行转绿验证
  - Run: `pytest tests/test_attached_cleanup.py tests/test_analysis.py -q`
  - Expected: PASS

### Task 4: Cleanup preview 红灯测试

**Files:**
- Modify: `codexsubmcp/core/cleanup.py`
- Create: `tests/test_cleanup_preview.py`

- [x] 写失败测试：`build_cleanup_preview()` 会把 `orphan_suites` 与 `stale_attached_branches` 统一成 targets
- [x] 写失败测试：preview summary 会正确统计 `target_count/orphan_suite_target_count/stale_branch_target_count`
- [x] 写失败测试：preview target 会携带 `reason/risk_hint/process_ids`
- [x] 写失败测试：没有 refresh/analyze 数据时不能构造 preview
- [x] 运行红灯验证
  - Run: `pytest tests/test_cleanup_preview.py -q`
  - Expected: FAIL，提示 preview builder 不存在
- [x] 实现最小 preview builder
- [x] 运行转绿验证
  - Run: `pytest tests/test_cleanup_preview.py -q`
  - Expected: PASS

### Task 5: Cleanup execution 红灯测试

**Files:**
- Modify: `codexsubmcp/core/cleanup.py`
- Create: `tests/test_cleanup_execution.py`

- [x] 写失败测试：执行 `orphan_suite` target 时会递归 kill 其 root launcher 并返回 suite 级动作结果
- [x] 写失败测试：执行 `stale_attached_branch` target 时会 kill stale launcher root 并记录 killed PIDs
- [x] 写失败测试：cleanup result summary 会统计 `closed_suite_count/closed_stale_branch_count/killed_mcp_instance_count/killed_process_count`
- [x] 写失败测试：当某个 target 执行失败时，只增加 `failed_target_count`，并保留其它成功动作
- [x] 运行红灯验证
  - Run: `pytest tests/test_cleanup_execution.py -q`
  - Expected: FAIL，提示 execution result 模型或 stale branch 执行能力缺失
- [x] 实现最小执行逻辑
- [x] 运行转绿验证
  - Run: `pytest tests/test_cleanup_execution.py -q`
  - Expected: PASS

### Task 6: Runtime logs 与累计统计红灯测试

**Files:**
- Create: `codexsubmcp/core/runtime_logs.py`
- Create: `tests/test_runtime_logs.py`

- [x] 写失败测试：refresh / preview / cleanup 会分别写出三类 JSON 日志文件
- [x] 写失败测试：cleanup success 才会进入 `LifetimeStats` 汇总
- [x] 写失败测试：preview / refresh 不会污染累计 `closed_suite/stale_branch/MCP/process` 统计
- [x] 写失败测试：`last_cleanup_at` 来自最新成功 cleanup 日志
- [x] 运行红灯验证
  - Run: `pytest tests/test_runtime_logs.py -q`
  - Expected: FAIL，提示日志 writer / stats 汇总不存在
- [x] 实现最小日志读写与累计统计汇总
- [x] 运行转绿验证
  - Run: `pytest tests/test_runtime_logs.py -q`
  - Expected: PASS

### Task 7: CLI 行为升级红灯测试

**Files:**
- Modify: `codexsubmcp/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_mcp_inventory.py`

- [x] 写失败测试：`scan mcp --format json` 只输出 `configured / running / drift`，不再输出 `installed_candidates`
- [x] 写失败测试：CLI 的 refresh/preview/cleanup headless 输出能返回新的 summary 字段
- [x] 写失败测试：cleanup headless 会写新的 cleanup 日志结构
- [x] 运行红灯验证
  - Run: `pytest tests/test_cli.py tests/test_mcp_inventory.py -q`
  - Expected: FAIL，提示 CLI 输出结构仍是旧版
- [x] 实现最小 CLI 适配
- [x] 运行转绿验证
  - Run: `pytest tests/test_cli.py tests/test_mcp_inventory.py -q`
  - Expected: PASS

### Task 8: GUI workflow 收口红灯测试

**Files:**
- Modify: `codexsubmcp/gui/main_window.py`
- Modify: `tests/test_gui_smoke.py`

- [x] 写失败测试：总览页只有 `刷新 / 预览清理 / 执行清理` 主按钮，不再有独立 `扫描 MCP`
- [x] 写失败测试：未 refresh 前，预览和执行按钮为禁用态或显示阻止信息
- [x] 写失败测试：`refresh` 成功后会同步更新 overview / MCP / cleanup / log 四页所需状态
- [x] 写失败测试：cleanup 成功后会自动再 refresh 一次
- [x] 运行红灯验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "activity_drawer_records_lifecycle_events or overview_buttons_dispatch_refresh_preview_and_cleanup or overview_page_shows_only_main_workflow_buttons or workflow_buttons_are_disabled_before_refresh or refresh_success_updates_pages_and_enables_workflow or cleanup_page_buttons_dispatch_preview_and_cleanup or mcp_page_refresh_button_dispatches_refresh or cleanup_success_triggers_follow_up_refresh"`
  - Expected: FAIL，提示 GUI workflow 仍依赖旧 scan-mcp 模型
- [x] 只实现主窗口状态收口和动作分发变更
- [x] 运行转绿验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "activity_drawer_records_lifecycle_events or overview_buttons_dispatch_refresh_preview_and_cleanup or overview_page_shows_only_main_workflow_buttons or workflow_buttons_are_disabled_before_refresh or refresh_success_updates_pages_and_enables_workflow or cleanup_page_buttons_dispatch_preview_and_cleanup or mcp_page_refresh_button_dispatches_refresh or cleanup_success_triggers_follow_up_refresh or main_window_uses_elevated_subprocess_for_cleanup_when_not_admin or main_window_refresh_success_updates_inventory_and_cleanup_summary or real_window_cleanup_runs_async_with_busy_feedback or real_window_mcp_refresh_runs_async_with_status_feedback"`
  - Expected: PASS

### Task 9: Overview 页面改造

**Files:**
- Modify: `codexsubmcp/gui/pages/overview_page.py`
- Modify: `tests/test_gui_smoke.py`

- [x] 写失败测试：总览显示 `运行中子代理 / 运行中 suite / 运行中 MCP 实例 / 已配置 MCP / 可清理目标`
- [x] 写失败测试：总览显示最近一次 cleanup 结果摘要
- [x] 写失败测试：总览显示累计清理统计
- [x] 写失败测试：总览的刷新时间与快照状态会更新
- [x] 运行红灯验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "overview"`
  - Expected: FAIL，提示仍是旧标签结构
- [x] 实现最小 Overview 渲染
- [x] 运行转绿验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "overview"`
  - Expected: PASS

### Task 10: MCP 页面改造

**Files:**
- Modify: `codexsubmcp/gui/pages/mcp_page.py`
- Modify: `tests/test_gui_smoke.py`

- [x] 写失败测试：MCP 页不再展示 installed candidates tab
- [x] 写失败测试：页面展示 configured 列表、running 列表与 drift 摘要
- [x] 写失败测试：每条 configured 记录展示 `source/command/env/timeouts`
- [x] 写失败测试：每条 running 记录展示 `tool_signature/instance_count/live_codex_pid_count/has_stale`
- [x] 运行红灯验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "mcp_page"`
  - Expected: FAIL，提示页面结构仍是 configured/installed 两栏
- [x] 实现最小 MCP 页渲染
- [x] 运行转绿验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "mcp_page"`
  - Expected: PASS

### Task 11: Cleanup 页面改造

**Files:**
- Modify: `codexsubmcp/gui/pages/cleanup_page.py`
- Modify: `tests/test_gui_smoke.py`

- [x] 写失败测试：cleanup 页面展示的是 preview targets，而不是单纯 suites 表
- [x] 写失败测试：target 行能区分 `orphan_suite` 与 `stale_attached_branch`
- [x] 写失败测试：详情面板会显示 stale branch 的 `tool_signature/latest_kept_launcher_pid`
- [x] 写失败测试：summary 显示本次预览预计清理规模
- [x] 运行红灯验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "cleanup_page"`
  - Expected: FAIL，提示旧 suites 表与详情格式不匹配
- [x] 实现最小 Cleanup 页改造
- [x] 运行转绿验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "cleanup_page"`
  - Expected: PASS

### Task 12: Log 页面改造

**Files:**
- Modify: `codexsubmcp/gui/pages/log_page.py`
- Modify: `tests/test_gui_smoke.py`

- [x] 写失败测试：日志列表会显示 `refresh / preview / cleanup` 三类摘要，而不是只有 action/status/文件名
- [x] 写失败测试：cleanup 日志会显示 `+suite / +stale / +MCP / +process` 摘要
- [x] 写失败测试：refresh 日志会显示当前态摘要
- [x] 写失败测试：详情区能显示完整 JSON 与错误信息
- [x] 运行红灯验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "log_page"`
  - Expected: FAIL，提示日志摘要仍是旧结构
- [x] 实现最小 Log 页改造
- [x] 运行转绿验证
  - Run: `pytest tests/test_gui_smoke.py -q -k "log_page"`
  - Expected: PASS

### Task 13: 全量回归与手工验证

**Files:**
- Modify: `README.md`
- Optional Create: `docs/manual-validation/2026-03-28-cleanup-redesign-checklist.md`

- [x] 运行核心测试集
  - Run: `pytest tests/test_codex_mcp_config.py tests/test_system_snapshot.py tests/test_analysis.py tests/test_cleanup_preview.py tests/test_cleanup_execution.py tests/test_runtime_logs.py tests/test_cli.py tests/test_gui_smoke.py -q`
  - Expected: PASS
- [x] 运行已有 cleanup 相关回归
  - Run: `pytest tests/test_core_cleanup.py tests/test_cleanup_codex_mcp_orphans.py tests/test_attached_cleanup.py -q`
  - Expected: PASS
- [ ] 手工验证：刷新会同时更新 configured/running/drift/current targets
- [ ] 手工验证：preview 后能看到 stale branch targets，不会直接执行 kill
- [ ] 手工验证：cleanup 后总览累计统计增加，日志页新增 cleanup 记录
- [ ] 手工验证：没有 refresh 时 GUI 不允许执行 cleanup
- [x] 根据结果更新 README / manual validation 文档
