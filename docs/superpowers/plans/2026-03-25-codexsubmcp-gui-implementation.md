# CodexSubMcp GUI Manager Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前脚本式 watchdog 仓库演进为可发布的 Windows GUI 管理器，支持单文件 `.exe`、计划任务管理、配置编辑、MCP 双层检索与 GitHub Release 分发。

**Architecture:** 在仓库中新增 `codexsubmcp/` 包，按 `core / platform / cli / gui` 四层拆分现有逻辑。先把 `tools/*.py` 中的清理、配置和任务计划逻辑下沉到核心模块，再通过统一 CLI 提供 headless 能力，最后让 PySide6 GUI 复用同一套后台命令，并补齐 PyInstaller 打包与 Release workflow。

**Tech Stack:** Python 3.12, PySide6, argparse, subprocess, dataclasses, json, pathlib, pytest, pytest-qt, PyInstaller, PowerShell

---

## Planned File Map

### Package Root

- Create: `codexsubmcp/__init__.py`
  - 包版本与公共导出
- Create: `codexsubmcp/__main__.py`
  - 统一程序入口，转发到 CLI
- Create: `codexsubmcp/cli.py`
  - `gui / run-once / dry-run / cleanup / task / scan / config` 子命令
- Create: `codexsubmcp/app_paths.py`
  - `%LOCALAPPDATA%\CodexSubMcpManager\...` 路径解析、目录创建、旧配置迁移

### Core

- Create: `codexsubmcp/core/__init__.py`
- Create: `codexsubmcp/core/models.py`
  - `ProcessInfo`、`ProcessSuite`、`CleanupReport`、`McpRecord`
- Create: `codexsubmcp/core/config.py`
  - 默认配置、配置加载、配置校验、导入导出
- Create: `codexsubmcp/core/cleanup.py`
  - suite 构建、分类、清理目标选择、dry-run 与执行报告
- Create: `codexsubmcp/core/mcp_inventory.py`
  - MCP 双层结果聚合、排序、置信度归一化

### Windows Platform

- Create: `codexsubmcp/platform/__init__.py`
- Create: `codexsubmcp/platform/windows/__init__.py`
- Create: `codexsubmcp/platform/windows/processes.py`
  - PowerShell 进程快照读取与解析
- Create: `codexsubmcp/platform/windows/tasks.py`
  - 计划任务安装、卸载、启停、状态读取、立即运行
- Create: `codexsubmcp/platform/windows/elevation.py`
  - `runas` 提权调用参数拼装
- Create: `codexsubmcp/platform/windows/install_artifact.py`
  - 稳定安装路径复制、版本覆盖策略
- Create: `codexsubmcp/platform/windows/mcp_sources.py`
  - Codex/Cursor/Claude 配置扫描、`npm -g`、PATH、Python 环境扫描

### GUI

- Create: `codexsubmcp/gui/__init__.py`
- Create: `codexsubmcp/gui/app.py`
  - QApplication 启动与主题初始化
- Create: `codexsubmcp/gui/task_runner.py`
  - 后台线程 / 异步任务桥接
- Create: `codexsubmcp/gui/main_window.py`
  - 左侧导航、状态条、日志抽屉与页面容器
- Create: `codexsubmcp/gui/pages/__init__.py`
- Create: `codexsubmcp/gui/pages/overview_page.py`
- Create: `codexsubmcp/gui/pages/cleanup_page.py`
- Create: `codexsubmcp/gui/pages/task_page.py`
- Create: `codexsubmcp/gui/pages/config_page.py`
- Create: `codexsubmcp/gui/pages/mcp_page.py`
- Create: `codexsubmcp/gui/pages/log_page.py`

### Legacy Compatibility

- Modify: `tools/cleanup_codex_mcp_orphans.py`
  - 变成对新核心的兼容入口
- Modify: `tools/install_codex_mcp_watchdog.py`
  - 变成对新 task CLI 的兼容入口
- Modify: `tools/uninstall_codex_mcp_watchdog.py`
  - 变成对新 task CLI 的兼容入口
- Modify: `tools/setup_codex_mcp_watchdog.py`
  - 明确标注 legacy / source 模式

### Packaging And Docs

- Modify: `pyproject.toml`
  - 增加 `PySide6` 与开发依赖
- Create: `packaging/windows/CodexSubMcpManager.spec`
  - PyInstaller 单文件打包配置
- Create: `.github/workflows/release.yml`
  - Windows 打包与 Release 上传
- Create: `docs/manual-validation/2026-03-25-codexsubmcp-gui-release-checklist.md`
  - UAC、计划任务、headless 与 GUI 实机验证清单
- Modify: `README.md`
  - GUI / Release 用法优先，源码脚本模式降级为 legacy

### Tests

- Create: `tests/test_app_paths.py`
- Create: `tests/test_core_cleanup.py`
- Create: `tests/test_core_config.py`
- Create: `tests/test_windows_tasks.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_mcp_inventory.py`
- Create: `tests/test_gui_smoke.py`
- Modify: `tests/test_cleanup_codex_mcp_orphans.py`
- Modify: `tests/test_install_codex_mcp_watchdog.py`
- Modify: `tests/test_uninstall_codex_mcp_watchdog.py`

---

### Task 1: 包结构与运行时路径红灯测试

**Files:**
- Modify: `pyproject.toml`
- Create: `codexsubmcp/__init__.py`
- Create: `codexsubmcp/__main__.py`
- Create: `codexsubmcp/app_paths.py`
- Create: `tests/test_app_paths.py`

- [ ] 写失败测试：`%LOCALAPPDATA%\CodexSubMcpManager` 下的 `config / logs / cache / exports / bin` 路径会被统一解析
- [ ] 写失败测试：首次启动会在缺失配置时生成默认 `config.json`
- [ ] 写失败测试：旧版 `temp/codex_mcp_watchdog/config.json` 可被识别为迁移来源
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_app_paths.py -q`
  - Expected: 至少 1 个 FAIL，提示 `codexsubmcp.app_paths` 或相关函数不存在
- [ ] 最小实现 `codexsubmcp` 包与 `app_paths.py`
- [ ] 在 `pyproject.toml` 增加：
  - `dependencies = ["PySide6>=6.8"]`
  - `dev = ["pytest>=8.0.0", "pytest-qt>=4.4", "PyInstaller>=6.0.0"]`
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_app_paths.py -q`
  - Expected: PASS
- [ ] 提交这一小步
  - Run: `git add pyproject.toml codexsubmcp tests/test_app_paths.py`
  - Run: `git commit -m "✨ feat(runtime): 新增桌面程序运行时路径"`

### Task 2: 清理核心与配置模型重构

**Files:**
- Create: `codexsubmcp/core/__init__.py`
- Create: `codexsubmcp/core/models.py`
- Create: `codexsubmcp/core/config.py`
- Create: `codexsubmcp/core/cleanup.py`
- Create: `codexsubmcp/platform/windows/processes.py`
- Create: `tests/test_core_config.py`
- Create: `tests/test_core_cleanup.py`
- Modify: `tests/test_cleanup_codex_mcp_orphans.py`
- Modify: `tools/cleanup_codex_mcp_orphans.py`

- [ ] 写失败测试：配置加载优先使用本地配置，其次才回退到默认模板
- [ ] 写失败测试：配置校验会拒绝无效的 `max_suites`、`interval_minutes`、空白 pattern
- [ ] 写失败测试：`build_candidate_suites`、`select_cleanup_suites` 返回结构化 `ProcessSuite`
- [ ] 写失败测试：dry-run 返回 `CleanupReport`，包含 suite 总数、清理目标与 actions
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_core_config.py tests/test_core_cleanup.py tests/test_cleanup_codex_mcp_orphans.py -q`
  - Expected: FAIL，提示新模块或结构化返回值不存在
- [ ] 从 `tools/cleanup_codex_mcp_orphans.py` 下沉代码到 `core/models.py`、`core/cleanup.py`、`platform/windows/processes.py`
- [ ] 实现 `core/config.py`，让默认配置来源不再绑死仓库 `temp/`
- [ ] 将 `tools/cleanup_codex_mcp_orphans.py` 改为兼容入口，内部调用新核心
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_core_config.py tests/test_core_cleanup.py tests/test_cleanup_codex_mcp_orphans.py -q`
  - Expected: PASS
- [ ] 提交这一小步
  - Run: `git add codexsubmcp/core codexsubmcp/platform/windows/processes.py tools/cleanup_codex_mcp_orphans.py tests/test_core_config.py tests/test_core_cleanup.py tests/test_cleanup_codex_mcp_orphans.py`
  - Run: `git commit -m "✨ feat(core): 抽离清理核心与配置模型"`

### Task 3: CLI 命令面与 headless 执行

**Files:**
- Create: `codexsubmcp/cli.py`
- Modify: `codexsubmcp/__main__.py`
- Create: `tests/test_cli.py`
- Modify: `tools/setup_codex_mcp_watchdog.py`

- [ ] 写失败测试：`python -m codexsubmcp --help` 暴露 `gui / run-once / dry-run / cleanup / task / scan / config`
- [ ] 写失败测试：`dry-run --headless` 输出结构化摘要，且默认不做真实清理
- [ ] 写失败测试：`config validate` 在配置合法时返回退出码 0
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_cli.py -q`
  - Expected: FAIL，提示 CLI 入口不存在或子命令缺失
- [ ] 实现 `cli.py` 的 argparse 命令树
- [ ] 让 `run-once --headless` 复用 cleanup 核心并把结果写入日志目录
- [ ] 将 `tools/setup_codex_mcp_watchdog.py` 标记为 legacy source-mode setup，并在输出中提示 GUI/Release 为推荐入口
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_cli.py -q`
  - Expected: PASS
- [ ] 补一轮真实帮助输出检查
  - Run: `python -m codexsubmcp --help`
  - Expected: 展示完整子命令列表
- [ ] 提交这一小步
  - Run: `git add codexsubmcp/cli.py codexsubmcp/__main__.py tools/setup_codex_mcp_watchdog.py tests/test_cli.py`
  - Run: `git commit -m "✨ feat(cli): 新增统一后台命令入口"`

### Task 4: Windows 计划任务、稳定安装路径与提权

**Files:**
- Create: `codexsubmcp/platform/windows/tasks.py`
- Create: `codexsubmcp/platform/windows/elevation.py`
- Create: `codexsubmcp/platform/windows/install_artifact.py`
- Create: `tests/test_windows_tasks.py`
- Modify: `tools/install_codex_mcp_watchdog.py`
- Modify: `tools/uninstall_codex_mcp_watchdog.py`
- Modify: `tests/test_install_codex_mcp_watchdog.py`
- Modify: `tests/test_uninstall_codex_mcp_watchdog.py`

- [ ] 写失败测试：任务注册命令直接指向 `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe run-once --headless`
- [ ] 写失败测试：稳定安装路径复制逻辑会覆盖旧版本并保留固定文件名
- [ ] 写失败测试：提权调用会把当前 exe 路径与目标子命令正确拼装到 `runas` 参数
- [ ] 写失败测试：`task status` 能解析已安装 / 未安装 / 启用 / 禁用
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_windows_tasks.py tests/test_install_codex_mcp_watchdog.py tests/test_uninstall_codex_mcp_watchdog.py -q`
  - Expected: FAIL，提示稳定路径、任务参数或状态模型不匹配
- [ ] 实现 `tasks.py` 的安装、卸载、启停、状态读取、立即运行
- [ ] 实现 `install_artifact.py`，把当前 exe 复制到稳定安装路径
- [ ] 实现 `elevation.py` 的 `runas` 参数构造
- [ ] 将 legacy `tools/install_codex_mcp_watchdog.py` 与 `tools/uninstall_codex_mcp_watchdog.py` 改为调用新 task API 的兼容入口
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_windows_tasks.py tests/test_install_codex_mcp_watchdog.py tests/test_uninstall_codex_mcp_watchdog.py -q`
  - Expected: PASS
- [ ] 提交这一小步
  - Run: `git add codexsubmcp/platform/windows tools/install_codex_mcp_watchdog.py tools/uninstall_codex_mcp_watchdog.py tests/test_windows_tasks.py tests/test_install_codex_mcp_watchdog.py tests/test_uninstall_codex_mcp_watchdog.py`
  - Run: `git commit -m "✨ feat(tasks): 新增计划任务与提权能力"`

### Task 5: MCP 双层检索引擎

**Files:**
- Create: `codexsubmcp/core/mcp_inventory.py`
- Create: `codexsubmcp/platform/windows/mcp_sources.py`
- Create: `tests/test_mcp_inventory.py`

- [ ] 写失败测试：配置文件来源会归类到 `configured`
- [ ] 写失败测试：`npm -g list --depth=0 --json` 扫描结果会归类到 `installed_candidate`
- [ ] 写失败测试：候选结果会带 `source`、`confidence`、`command/path` 与排序结果
- [ ] 写失败测试：`scan mcp --format json` 返回可供 GUI 直接消费的 JSON 结构
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_mcp_inventory.py tests/test_cli.py -q`
  - Expected: FAIL，提示 MCP 模型或 JSON 输出不存在
- [ ] 实现 `mcp_sources.py` 的配置文件扫描、`npm -g` 扫描、PATH 扫描与 Python 环境扫描
- [ ] 实现 `mcp_inventory.py` 的聚合与置信度归一化
- [ ] 将 `scan mcp --format json` 接入 CLI
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_mcp_inventory.py tests/test_cli.py -q`
  - Expected: PASS
- [ ] 手工检查 JSON 输出结构
  - Run: `python -m codexsubmcp scan mcp --format json`
  - Expected: 顶层至少包含 `configured` 与 `installed_candidates`
- [ ] 提交这一小步
  - Run: `git add codexsubmcp/core/mcp_inventory.py codexsubmcp/platform/windows/mcp_sources.py codexsubmcp/cli.py tests/test_mcp_inventory.py tests/test_cli.py`
  - Run: `git commit -m "✨ feat(mcp): 新增双层检索能力"`

### Task 6: GUI 框架、导航与后台任务桥接

**Files:**
- Create: `codexsubmcp/gui/__init__.py`
- Create: `codexsubmcp/gui/app.py`
- Create: `codexsubmcp/gui/task_runner.py`
- Create: `codexsubmcp/gui/main_window.py`
- Create: `codexsubmcp/gui/pages/__init__.py`
- Create: `codexsubmcp/gui/pages/overview_page.py`
- Create: `codexsubmcp/gui/pages/cleanup_page.py`
- Create: `codexsubmcp/gui/pages/task_page.py`
- Create: `tests/test_gui_smoke.py`

- [ ] 写失败测试：主窗口能启动，并包含 `总览 / 清理 / 计划任务 / 配置 / MCP 检索 / 日志` 导航项
- [ ] 写失败测试：点击 `立即预览` 会向后台 task runner 派发 dry-run 动作
- [ ] 写失败测试：计划任务页能渲染当前任务状态摘要
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_gui_smoke.py -q`
  - Expected: FAIL，提示 GUI 模块或页面不存在
- [ ] 实现 `gui/app.py`、`gui/task_runner.py` 与 `gui/main_window.py`
- [ ] 最小实现 `overview_page.py`、`cleanup_page.py`、`task_page.py`
- [ ] 将 `python -m codexsubmcp gui` 接入 QApplication 启动
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_gui_smoke.py -q`
  - Expected: PASS
- [ ] 手工启动 GUI 检查无崩溃
  - Run: `python -m codexsubmcp gui`
  - Expected: 主窗口可打开并切换页面
- [ ] 提交这一小步
  - Run: `git add codexsubmcp/gui codexsubmcp/cli.py tests/test_gui_smoke.py`
  - Run: `git commit -m "✨ feat(gui): 搭建主窗口与基础页面"`

### Task 7: 配置编辑、MCP 页面与日志页完善

**Files:**
- Create: `codexsubmcp/gui/pages/config_page.py`
- Create: `codexsubmcp/gui/pages/mcp_page.py`
- Create: `codexsubmcp/gui/pages/log_page.py`
- Modify: `tests/test_gui_smoke.py`
- Modify: `README.md`

- [ ] 写失败测试：配置页可加载并回显当前配置
- [ ] 写失败测试：配置校验失败时会在 GUI 中显示错误，不会静默覆盖文件
- [ ] 写失败测试：MCP 页面能分栏显示 `configured` 与 `installed_candidate`
- [ ] 写失败测试：日志页能列出日志文件并显示选中文件内容
- [ ] 运行红灯验证
  - Run: `python -m pytest tests/test_gui_smoke.py -q`
  - Expected: FAIL，提示新增页面和数据绑定不存在
- [ ] 实现 `config_page.py` 的表单模式与 JSON 模式
- [ ] 实现 `mcp_page.py` 的双列表展示与刷新动作
- [ ] 实现 `log_page.py` 的日志列表与详情视图
- [ ] 更新 `README.md`，把 GUI/Release 用法移到前面，脚本模式标记为 legacy
- [ ] 运行转绿验证
  - Run: `python -m pytest tests/test_gui_smoke.py tests/test_cli.py tests/test_mcp_inventory.py -q`
  - Expected: PASS
- [ ] 提交这一小步
  - Run: `git add codexsubmcp/gui/pages README.md tests/test_gui_smoke.py tests/test_cli.py tests/test_mcp_inventory.py`
  - Run: `git commit -m "✨ feat(gui): 完成配置编辑与MCP页面"`

### Task 8: PyInstaller 打包、GitHub Release 与手工验收

**Files:**
- Create: `packaging/windows/CodexSubMcpManager.spec`
- Create: `.github/workflows/release.yml`
- Create: `docs/manual-validation/2026-03-25-codexsubmcp-gui-release-checklist.md`
- Modify: `README.md`

- [ ] 写失败测试或校验脚本：PyInstaller spec 引用 `codexsubmcp.__main__`，产物名为 `CodexSubMcpManager`
- [ ] 写失败校验：Release workflow 仅在 Windows runner 上打包，并上传 `.exe`
- [ ] 运行静态校验
  - Run: `python -m pytest tests/test_cli.py -q`
  - Expected: 既有 CLI 仍为 PASS，说明打包配置未破坏入口
- [ ] 实现 `packaging/windows/CodexSubMcpManager.spec`
- [ ] 实现 `.github/workflows/release.yml`
- [ ] 编写手工验收清单，覆盖：
  - 首次启动生成配置
  - dry-run
  - 真实清理
  - 安装计划任务
  - 卸载计划任务
  - `run-once --headless`
  - GUI 中扫描 MCP
  - 下载 Release 到无 Python 机器后启动
- [ ] 执行本地打包验证
  - Run: `pyinstaller packaging/windows/CodexSubMcpManager.spec --noconfirm`
  - Expected: 生成 `dist/CodexSubMcpManager.exe`
- [ ] 执行最终自动化验证
  - Run: `python -m pytest -q`
  - Expected: PASS
- [ ] 执行手工验证清单并记录结果
- [ ] 提交这一小步
  - Run: `git add packaging .github docs/manual-validation README.md`
  - Run: `git commit -m "🔧 build(release): 增加GUI打包与发布流程"`

### Task 9: 收尾与兼容性复核

**Files:**
- Modify: `README.md`
- Test: `tools/cleanup_codex_mcp_orphans.py`
- Test: `tools/install_codex_mcp_watchdog.py`
- Test: `tools/uninstall_codex_mcp_watchdog.py`

- [ ] 逐个运行 legacy 入口，确认仍能输出明确提示或兼容执行
  - Run: `python tools/cleanup_codex_mcp_orphans.py --help`
  - Run: `python tools/install_codex_mcp_watchdog.py --help`
  - Run: `python tools/uninstall_codex_mcp_watchdog.py --help`
- [ ] 复核 README 中的 GUI 与 legacy 路径说明没有冲突
- [ ] 运行一次完整状态检查
  - Run: `git status -sb`
  - Expected: 只有本次任务相关改动
- [ ] 如验证全部完成，准备进入 `requesting-code-review` / `/review`

## Notes For Executor

- 现有 `tools/*.py` 中已有可复用逻辑，不要在 GUI 里重复实现
- GUI 页面单文件不应超过 300 行；一旦超过就拆出小组件
- 所有系统调用都要留出可 mock 接口，避免 GUI 测试依赖真实 Windows 状态
- 真实清理、计划任务安装与 UAC 行为必须在最终阶段单独做手工验证
- 不要在未完成 `python -m pytest -q` 和至少一次本地打包前宣称“可发布”
