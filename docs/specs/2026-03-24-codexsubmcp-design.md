# Codexsubmcp 设计

## 目标

- 识别 Windows 上 Codex / subagent 残留的 MCP 孤儿套件
- 默认保留最新 6 套，只清理超额旧套件
- 提供一键安装脚本，注册定时巡检任务
- 支持把仓库同步到另一台电脑后直接复用

## 方案

采用 `Python 清理核心 + PowerShell 安装/运行包装器`：

- `tools/cleanup_codex_mcp_orphans.py`
  - 枚举 Windows 进程
  - 按 PPID 和启动时间识别 MCP 套件
  - dry-run 预览与实际清理
- `tools/install_codex_mcp_watchdog.py`
  - 初始化本地 config
  - 注册计划任务
- `tools/install_codex_mcp_watchdog.ps1`
  - 用户入口
- `tools/run_codex_mcp_watchdog.ps1`
  - 计划任务实际执行入口

## 本地状态

- 仓库模板：`tools/codex_mcp_watchdog.example.json`
- 本地生效配置：`temp/codex_mcp_watchdog/config.json`
- 日志目录：`temp/codex_mcp_watchdog/logs/`

## GitHub

- 交付为独立公开仓库
- 本地先完成 git 初始化与首个 commit
- 若当前机器无 GitHub 凭据，则保留到最后一步显式提示用户补一次登录

