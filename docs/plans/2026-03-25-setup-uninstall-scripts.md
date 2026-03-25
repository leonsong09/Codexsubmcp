# Setup And Uninstall Scripts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Codexsubmcp 补一键初始化安装脚本和卸载计划任务脚本，让另一台 Windows 机器可以直接 setup，也能干净地移除计划任务。

**Architecture:** 保持现有 `install_codex_mcp_watchdog.py` 为计划任务注册器；新增 `setup_codex_mcp_watchdog.py/.ps1` 负责创建虚拟环境、安装依赖、跑 dry-run 和调用现有安装器；新增 `uninstall_codex_mcp_watchdog.py/.ps1` 负责注销计划任务。测试优先覆盖命令序列、PowerShell 包装器和卸载脚本内容。

**Tech Stack:** Python, argparse, subprocess, PowerShell, pytest

---

### Task 1: Setup 脚本红灯测试

**Files:**
- Modify: `tests/test_install_codex_mcp_watchdog.py`
- Create: `tools/setup_codex_mcp_watchdog.py`
- Create: `tools/setup_codex_mcp_watchdog.ps1`

- [ ] 写失败测试：缺少 `venv` 时，setup 会先创建 `venv`
- [ ] 写失败测试：setup 会按顺序执行 `pip install -e .[dev]`、dry-run、注册计划任务
- [ ] 写失败测试：PowerShell setup 包装器会优先复用 `venv`，否则回退到系统 `python.exe`
- [ ] 运行 focused pytest，确认红灯

### Task 2: Uninstall 脚本红灯测试

**Files:**
- Create: `tests/test_uninstall_codex_mcp_watchdog.py`
- Create: `tools/uninstall_codex_mcp_watchdog.py`
- Create: `tools/uninstall_codex_mcp_watchdog.ps1`

- [ ] 写失败测试：卸载脚本生成 `Unregister-ScheduledTask` 命令
- [ ] 写失败测试：PowerShell uninstall 包装器指向 Python 卸载器
- [ ] 运行 focused pytest，确认红灯

### Task 3: 最小实现与文档

**Files:**
- Modify: `README.md`
- Modify: `tools/install_codex_mcp_watchdog.py`
- Create: `tools/setup_codex_mcp_watchdog.py`
- Create: `tools/setup_codex_mcp_watchdog.ps1`
- Create: `tools/uninstall_codex_mcp_watchdog.py`
- Create: `tools/uninstall_codex_mcp_watchdog.ps1`

- [ ] 实现 setup Python 逻辑与 `.ps1` 包装器
- [ ] 实现 uninstall Python 逻辑与 `.ps1` 包装器
- [ ] 更新 README：一键 setup / uninstall 用法
- [ ] 运行 focused pytest，确认转绿

### Task 4: 实机验证与发布

**Files:**
- Test: `tests/test_install_codex_mcp_watchdog.py`
- Test: `tests/test_uninstall_codex_mcp_watchdog.py`

- [ ] 实机运行 setup 脚本或核心路径，确认可成功执行
- [ ] 实机运行 uninstall 脚本，确认任务会被移除
- [ ] 重新安装一次计划任务，恢复当前机器状态
- [ ] 提交并 push 到 `origin/main`
