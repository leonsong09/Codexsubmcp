# Codexsubmcp Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个独立的 Windows 工具仓库，用于识别并清理 Codex subagent 泄漏的 MCP 套件，并提供一键安装巡检任务的入口。

**Architecture:** 使用 Python 标准库实现进程快照解析、PPID lineage 分析、suite 聚类与清理策略；使用 PowerShell 包装安装入口与 watchdog 运行入口；本地状态收敛到 `temp/`，源码仓库只提交模板和脚本。

**Tech Stack:** Python, argparse, dataclasses, json, subprocess, PowerShell, pytest

---

### Task 1: 清理核心红灯测试

**Files:**
- Create: `tests/test_cleanup_codex_mcp_orphans.py`
- Create: `tools/cleanup_codex_mcp_orphans.py`

- [ ] 写失败测试：基于 PPID 判定 live codex / orphan suite
- [ ] 写失败测试：按时间窗口聚类 MCP roots
- [ ] 写失败测试：只清理超额旧 orphan suites
- [ ] 写失败测试：dry-run 不执行 kill
- [ ] 运行 focused pytest，确认红灯

### Task 2: 安装器红灯测试

**Files:**
- Create: `tests/test_install_codex_mcp_watchdog.py`
- Create: `tools/install_codex_mcp_watchdog.py`
- Create: `tools/install_codex_mcp_watchdog.ps1`
- Create: `tools/run_codex_mcp_watchdog.ps1`
- Create: `tools/codex_mcp_watchdog.example.json`

- [ ] 写失败测试：优先使用项目 `venv` Python
- [ ] 写失败测试：首次安装会创建本地 config
- [ ] 写失败测试：生成的计划任务脚本包含 runner、任务名和 10 分钟重复间隔
- [ ] 写失败测试：PowerShell 包装器指向 Python 安装器
- [ ] 运行 focused pytest，确认红灯

### Task 3: 最小实现与验证

**Files:**
- Modify: `tools/cleanup_codex_mcp_orphans.py`
- Modify: `tools/install_codex_mcp_watchdog.py`
- Modify: `tests/test_cleanup_codex_mcp_orphans.py`
- Modify: `tests/test_install_codex_mcp_watchdog.py`
- Modify: `README.md`

- [ ] 实现最小清理逻辑，让 focused tests 转绿
- [ ] 实现安装与运行脚本，让 focused tests 转绿
- [ ] 补 README 使用说明
- [ ] 跑 focused pytest
- [ ] 手工 dry-run 复核输出

### Task 4: 仓库初始化与发布

**Files:**
- Create: `README.md`

- [ ] 初始化本地 git 仓库
- [ ] 形成首个 commit
- [ ] 如凭据可用则创建 public GitHub repo 并 push
- [ ] 如凭据缺失，明确留下最后一步阻塞说明

