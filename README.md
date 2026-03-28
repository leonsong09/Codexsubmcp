# CodexSubMcp

Windows watchdog and desktop manager for leaked Codex subagent MCP process suites.

## Release 优先

默认推荐直接使用 GitHub Release 中的单文件 GUI，而不是源码脚本模式。

### 适用场景

- Windows 机器
- Codex subagent / 多 agent 并行场景
- MCP 进程没有随 agent 退出，逐渐堆积成孤儿套件
- 需要在没有 Python 的机器上直接运行

### 主要能力

- 单文件 `CodexSubMcpManager.exe`
- 围绕 **刷新 → 预览 → 清理 → 日志** 的单一主流程
- 展示当前运行态：
  - 运行中子代理数量
  - 运行中 suite 数量
  - 运行中 MCP 实例数量
  - 已配置 MCP 数量
- 同时支持两类清理目标：
  - `orphan_suite`
  - `stale_attached_branch`
- MCP 页只展示：
  - configured
  - running
  - drift
- 总览支持累计清理统计
- 日志页支持 `refresh / preview / cleanup` 三类历史回放
- 管理员动作支持按需提权

## Release 使用

1. 下载 `CodexSubMcpManager.exe`
2. 双击启动 GUI
3. 先在 `总览` 页执行一次 `刷新`
4. 再执行 `预览清理`
5. 确认后执行 `执行清理`
6. 如需后台巡检，在 `计划任务` 页安装 `CodexSubMcpWatchdog`

### 运行时目录

- `%LOCALAPPDATA%\CodexSubMcpManager\config.json`
- `%LOCALAPPDATA%\CodexSubMcpManager\logs\`
- `%LOCALAPPDATA%\CodexSubMcpManager\cache\`
- `%LOCALAPPDATA%\CodexSubMcpManager\exports\`
- `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe`

### GUI 页面

- `总览`
- `清理`
- `计划任务`
- `配置`
- `MCP 检索`
- `日志`

### CLI 命令面

```powershell
CodexSubMcpManager.exe gui
CodexSubMcpManager.exe refresh --headless
CodexSubMcpManager.exe preview --headless
CodexSubMcpManager.exe dry-run --headless
CodexSubMcpManager.exe cleanup --yes --headless
CodexSubMcpManager.exe cleanup --yes --headless --report-file cleanup-report.json
CodexSubMcpManager.exe run-once --headless
CodexSubMcpManager.exe task install --interval 10
CodexSubMcpManager.exe task uninstall
CodexSubMcpManager.exe task status --format json
CodexSubMcpManager.exe task enable
CodexSubMcpManager.exe task disable
CodexSubMcpManager.exe scan mcp --format json
CodexSubMcpManager.exe config validate
CodexSubMcpManager.exe config reset
```

## 当前发布版状态

本版本已经补齐：

- Codex `config.toml` / 项目 `.codex/config.toml` 的 MCP 读取
- `state_5.sqlite` open 子代理统计
- 当前运行态分析（running / drift / stale）
- `orphan_suite + stale_attached_branch` 双目标清理
- `refresh / preview / cleanup` 三类结构化日志
- 累计清理统计
- GUI 主流程收口
- 计划任务管理员动作按需提权
- 真实清理管理员动作按需提权，并通过结构化报告回传 GUI

对应 release 文案见：

- `docs/release-notes/2026-03-28-v0.3.0-cleanup-redesign.md`

对外公告文案见：

- `docs/release-announcements/2026-03-28-v0.3.0-end-user.md`

维护者发布流程见：

- `docs/release-process.md`

对应手工验收清单见：

- `docs/manual-validation/2026-03-25-codexsubmcp-gui-release-checklist.md`
- `docs/manual-validation/2026-03-28-cleanup-redesign-checklist.md`

## 源码模式（Legacy）

如果你只是本地调试仓库，仍然可以使用旧的源码模式。

### 环境初始化

```powershell
git clone https://github.com/leonsong09/Codexsubmcp.git
cd Codexsubmcp
python -m venv venv
venv\Scripts\python.exe -m pip install -e .[dev]
```

### 常用源码命令

```powershell
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py --yes
venv\Scripts\python.exe tools\install_codex_mcp_watchdog.py --interval-minutes 5
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\setup_codex_mcp_watchdog.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\uninstall_codex_mcp_watchdog.ps1
```

legacy 运行时配置仍在：

- `temp\codex_mcp_watchdog\config.json`
- `temp\codex_mcp_watchdog\logs\`

## 识别范围

默认识别关键字包括：

- `codex.exe`
- `@modelcontextprotocol/*`
- `agentation-mcp`
- `mcp-server-fetch`
- `ace-tool`
- `auggie`

工具会：

- 扫描 Windows 原生进程树
- 读取 Codex MCP TOML 配置
- 读取 `thread_spawn_edges.status='open'` 统计子代理数
- 按 PPID lineage 和启动时间窗口聚类为 MCP suites
- 识别 live Codex 下重复拉起的 stale MCP branches
- 先预览，再清理

## 验证

当前已验证：

- `pytest tests/test_cli.py tests/test_mcp_inventory.py tests/test_runtime_logs.py tests/test_cleanup_preview.py tests/test_cleanup_execution.py tests/test_core_cleanup.py tests/test_cleanup_codex_mcp_orphans.py tests/test_attached_cleanup.py tests/test_analysis.py tests/test_system_snapshot.py tests/test_codex_mcp_config.py tests/test_app_paths.py tests/test_gui_smoke.py -q`
- `pytest -q`

最近一轮完整结果：

- GUI smoke: `39 passed`
- 全量测试: `107 passed`
