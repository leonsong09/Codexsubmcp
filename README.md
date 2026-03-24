# Codexsubmcp

Windows watchdog for leaked Codex subagent MCP process suites.

## 作用

当 Codex 在 subagent / 多 agent 并行场景下重复拉起 MCP，而部分 MCP 没有随 agent 退出时，这个工具会：

- 扫描 Windows 原生进程树
- 识别 `codex.exe`、`@modelcontextprotocol/*`、`agentation-mcp`、`mcp-server-fetch`、`ace-tool`、`auggie` 等相关进程
- 按 PPID lineage 和启动时间窗口聚类为 MCP suites
- 默认保留最新 `6` 套
- 只清理超额的旧 orphan suites

## 快速开始

### 1. 创建本地虚拟环境

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -e .[dev]
```

### 2. 手工预览

默认是 dry-run：

```powershell
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py
```

### 3. 注册自动巡检

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_codex_mcp_watchdog.ps1
```

安装后会：

- 复制本地配置到 `temp\codex_mcp_watchdog\config.json`
- 注册计划任务 `CodexSubMcpWatchdog`
- 通过 `tools\run_codex_mcp_watchdog.ps1` 每 10 分钟巡检一次

## 本地配置

模板文件：

- `tools\codex_mcp_watchdog.example.json`

实际运行配置：

- `temp\codex_mcp_watchdog\config.json`

常用字段：

- `max_suites`
- `suite_window_seconds`
- `codex_patterns`
- `candidate_patterns`

## 测试

```powershell
python -m pytest tests\test_cleanup_codex_mcp_orphans.py tests\test_install_codex_mcp_watchdog.py -q
```

## GitHub 发布

当前仓库可直接本地初始化并提交。

如果机器已经有 GitHub CLI 或 token，可继续创建 public repo 并 push；如果没有，需要补一次 GitHub 登录态后再执行远端创建。
