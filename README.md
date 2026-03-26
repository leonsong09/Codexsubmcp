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
- GUI 管理 `dry-run`、真实清理、计划任务、配置、MCP 检索、日志
- 计划任务直接指向稳定安装路径中的发布产物
- 清理页支持 suites 表格、详情面板、复制和导出
- 配置页支持 `表单 / JSON` 双模式编辑
- MCP 页支持双 Tab、详情面板、复制和导出
- 日志页支持过滤、导出、打开日志目录
- 管理员动作支持按需提权

## Release 使用

1. 下载 `CodexSubMcpManager.exe`
2. 双击启动 GUI
3. 在 `总览` 或 `清理` 页先执行一次 `立即预览`
4. 如需后台巡检，在 `计划任务` 页安装 `CodexSubMcpWatchdog`

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

- 顶部状态条
- 底部活动抽屉
- 总览快捷操作
- 清理详情面板
- 计划任务安装 / 重装 / 启停 / 卸载
- 配置双模式
- MCP 双层检索
- 日志过滤与导出
- 计划任务管理员动作按需提权
- 真实清理管理员动作按需提权，并通过结构化报告回传 GUI

对应 release 文案见：

- `docs/release-notes/2026-03-26-gui-alignment-release.md`

对应手工验收清单见：

- `docs/manual-validation/2026-03-25-codexsubmcp-gui-release-checklist.md`

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
- 按 PPID lineage 和启动时间窗口聚类为 MCP suites
- 默认保留最新 `6` 套
- 只清理超额的旧 orphan suites

## 验证

当前已验证：

- `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui_smoke.py -q`
- `QT_QPA_PLATFORM=offscreen python -m pytest -q`
- `pyinstaller packaging/windows/CodexSubMcpManager.spec --noconfirm`

最近一轮完整结果：

- GUI smoke: `35 passed`
- 全量测试: `75 passed`
- PyInstaller: 构建成功
