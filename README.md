# Codexsubmcp

Windows watchdog for leaked Codex subagent MCP process suites.

## 作用

当 Codex 在 subagent / 多 agent 并行场景下重复拉起 MCP，而部分 MCP 没有随 agent 退出时，这个工具会：

- 扫描 Windows 原生进程树
- 识别 `codex.exe`、`@modelcontextprotocol/*`、`agentation-mcp`、`mcp-server-fetch`、`ace-tool`、`auggie` 等相关进程
- 按 PPID lineage 和启动时间窗口聚类为 MCP suites
- 默认保留最新 `6` 套
- 只清理超额的旧 orphan suites

## 适用范围

- 平台：Windows
- 目标问题：Codex subagent / 多 agent 模式下，MCP 没有跟随退出，逐渐堆积成孤儿进程
- 默认识别关键字：
  - `codex.exe`
  - `@modelcontextprotocol/*`
  - `agentation-mcp`
  - `mcp-server-fetch`
  - `ace-tool`
  - `auggie`

## 快速开始

### 1. 克隆仓库

```powershell
git clone https://github.com/leonsong09/Codexsubmcp.git
cd Codexsubmcp
```

### 2. 创建本地虚拟环境

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -e .[dev]
```

### 3. 手工预览

默认是 dry-run：

```powershell
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py
```

### 4. 注册自动巡检

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\install_codex_mcp_watchdog.ps1
```

安装后会：

- 复制本地配置到 `temp\codex_mcp_watchdog\config.json`
- 注册计划任务 `CodexSubMcpWatchdog`
- 通过 `tools\run_codex_mcp_watchdog.ps1` 每 10 分钟巡检一次

### 5. 一键初始化

如果你不想手工分步执行，可以直接运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\setup_codex_mcp_watchdog.ps1
```

这个脚本会自动：

- 创建或复用项目 `venv`
- 安装 `-e .[dev]`
- 跑一次 dry-run
- 注册计划任务

## 另一台电脑如何配置

```powershell
cd D:\Documents\Code\Tools
git clone https://github.com/leonsong09/Codexsubmcp.git
cd Codexsubmcp

python -m venv venv
venv\Scripts\python.exe -m pip install -e .

venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\install_codex_mcp_watchdog.ps1
```

推荐先跑一次 dry-run，再安装计划任务。

如果希望一步完成，也可以直接运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\setup_codex_mcp_watchdog.ps1
```

## 验证

### 检查计划任务

```powershell
Get-ScheduledTask -TaskName CodexSubMcpWatchdog
```

### 检查本地配置

```powershell
Get-Content temp\codex_mcp_watchdog\config.json
```

### 再做一次手工 dry-run

```powershell
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py
```

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

如果不同机器上的 MCP 组合不同，优先改 `candidate_patterns`，不要直接改源码。

## 常用命令

### 只预览，不清理

```powershell
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py
```

### 立即执行一次真实清理

```powershell
venv\Scripts\python.exe tools\cleanup_codex_mcp_orphans.py --yes
```

### 重新安装任务，并改成每 5 分钟巡检

```powershell
venv\Scripts\python.exe tools\install_codex_mcp_watchdog.py --interval-minutes 5
```

### 一键初始化安装

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\setup_codex_mcp_watchdog.ps1
```

### 卸载计划任务

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\uninstall_codex_mcp_watchdog.ps1
```

默认只会移除 `CodexSubMcpWatchdog` 计划任务，不会删除本地配置和日志。

## 日志

- 配置目录：`temp\codex_mcp_watchdog\`
- 运行日志：`temp\codex_mcp_watchdog\logs\`

## 测试

```powershell
venv\Scripts\python.exe -m pytest tests\test_cleanup_codex_mcp_orphans.py tests\test_install_codex_mcp_watchdog.py -q
```

## 当前状态

- 仓库：`https://github.com/leonsong09/Codexsubmcp`
- 已验证：
  - focused pytest 通过
  - 本机 dry-run 可正常输出
  - 计划任务 `CodexSubMcpWatchdog` 可正常注册
