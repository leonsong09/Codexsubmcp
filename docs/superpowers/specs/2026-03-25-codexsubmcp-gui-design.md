# CodexSubMcp GUI 管理器设计

## 背景

当前仓库已经具备：

- `tools/cleanup_codex_mcp_orphans.py`
  - 扫描 Windows 进程
  - 识别 Codex / MCP suites
  - 支持 dry-run 与真实清理
- `tools/install_codex_mcp_watchdog.py`
  - 初始化本地配置
  - 注册计划任务
- `tools/setup_codex_mcp_watchdog.py`
  - 创建虚拟环境
  - 安装依赖
  - 跑一次 dry-run
  - 调用安装器
- PowerShell 包装脚本
  - `install_codex_mcp_watchdog.ps1`
  - `run_codex_mcp_watchdog.ps1`
  - `setup_codex_mcp_watchdog.ps1`
  - `uninstall_codex_mcp_watchdog.ps1`

这套方案适合源码仓库模式，但不适合以下目标：

- 在没有 Python 的 Windows 机器上直接运行
- 发布到 GitHub Release 供最终用户下载
- 用统一 GUI 管理清理、计划任务、配置和 MCP 检索

因此本次设计的目标是把当前仓库从“脚本集合”扩展为“可发布的桌面管理工具”。

## 目标

- 提供一个单文件 `.exe` GUI，支持无 Python 环境的 Windows 机器直接运行
- GUI 统一管理：
  - dry-run
  - 真实清理
  - 计划任务安装、卸载、启停、重装
  - 完整配置编辑
  - MCP 双层检索
  - 日志与状态查看
- 支持 GitHub Release 分发
- 保留并复用现有 Python 清理核心，而不是推倒重写
- 让计划任务直接调用发布产物本身，不依赖仓库路径、`venv` 或 `.ps1`

## 非目标

- 首版不做自动更新
- 首版不做 MSI / NSIS 安装器
- 首版不承诺 100% 枚举出系统中所有 MCP 安装来源
- 首版不兼容非 Windows 平台

## 方案选择

候选方案：

- A. `Tkinter + PyInstaller`
  - 优点：依赖轻，实现快
  - 缺点：复杂管理界面可维护性差，发布质感不足
- B. `PySide6 + PyInstaller`
  - 优点：复用现有 Python 逻辑，GUI 能力足够支撑表格、配置编辑、日志、状态面板
  - 缺点：包体更大，打包链更重
- C. `.NET WPF/WinUI`
  - 优点：Windows 原生集成度高
  - 缺点：需要重写现有 Python 核心，成本过高

最终选择：

- `PySide6 + PyInstaller`

选择理由：

- 现有核心逻辑已经在 Python 中
- 可以把核心逻辑、后台命令、GUI、打包链统一在一个技术栈中
- 比 `Tkinter` 更适合做发布级桌面工具
- 比重写为 `.NET` 的风险更低、落地更快

## 总体架构

建议将代码拆为四层：

- `core`
  - suite 聚类
  - 清理策略
  - 配置模型
  - MCP 检索模型
- `platform/windows`
  - 管理员提权
  - 计划任务安装与状态读取
  - Windows 路径与数据目录管理
  - 常见 MCP 安装源扫描
- `cli`
  - GUI、计划任务和提权子进程共用的后台命令入口
- `gui`
  - 主窗口
  - 页面导航
  - 异步任务调度
  - 日志展示

### 分层原则

- GUI 不能直接承担业务逻辑
- 计划任务不能再依赖仓库内的 PowerShell wrapper
- 所有后台动作都应通过统一 CLI 命令层暴露
- 现有 `tools/*.py` 中可复用逻辑应逐步下沉到 `core` / `platform`

## 运行模式

桌面程序提供两种运行形态：

- 交互式 GUI
  - 用户双击 `.exe` 启动
  - 默认非管理员权限
  - 提供可视化操作面板
- 后台 headless 模式
  - 供计划任务和提权子进程调用
  - 无窗口
  - 输出结构化结果与日志

建议保留的后台命令面：

```text
CodexSubMcpManager.exe gui
CodexSubMcpManager.exe run-once --headless
CodexSubMcpManager.exe dry-run --headless
CodexSubMcpManager.exe cleanup --yes --headless
CodexSubMcpManager.exe task install --interval 10
CodexSubMcpManager.exe task uninstall
CodexSubMcpManager.exe task status
CodexSubMcpManager.exe task enable
CodexSubMcpManager.exe task disable
CodexSubMcpManager.exe scan mcp --format json
CodexSubMcpManager.exe config validate
CodexSubMcpManager.exe config reset
```

这样设计的目的：

- GUI 点击按钮时，只是调用统一后台命令
- 计划任务直接执行发布产物自己的 headless 命令
- 提权操作可由 GUI 拉起同一个 `.exe` 的管理员子进程完成
- CLI 层可直接参与集成测试

## 数据目录与运行时状态

发布版不再把运行状态写入仓库目录，而是统一写入：

- `%LOCALAPPDATA%\CodexSubMcpManager\config.json`
- `%LOCALAPPDATA%\CodexSubMcpManager\logs\`
- `%LOCALAPPDATA%\CodexSubMcpManager\cache\`
- `%LOCALAPPDATA%\CodexSubMcpManager\exports\`
- `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe`

### 原则

- 首次启动时，如果配置不存在，则基于内置默认模板生成
- 配置、日志和导出目录必须与程序路径解耦
- 计划任务使用稳定安装路径中的 `.exe`
- 不再依赖仓库中的 `temp/`

### 迁移

如用户从源码版迁移，GUI 可提供：

- 导入旧版 `temp/codex_mcp_watchdog/config.json`
- 将旧配置转换为新版结构

## 提权策略

程序默认以普通权限启动，仅在需要管理员权限的动作上按需提权。

需要管理员权限的动作包括：

- 安装计划任务
- 卸载计划任务
- 重装计划任务
- 启用 / 禁用计划任务
- 部分真实清理动作
- 个别需要访问系统级安装信息的扫描命令

不需要管理员权限的动作包括：

- dry-run
- 查看日志
- 编辑配置
- 查看当前状态
- 大部分 MCP 检索

### 提权机制

- GUI 主进程普通权限运行
- 用户触发管理员动作时，GUI 以 `runas` 方式拉起同一程序的子命令
- 子进程只执行单一动作并返回结果
- GUI 读取结果后刷新页面状态

这样可以避免：

- 程序一启动就触发 UAC
- 非管理员操作也被放大权限
- GUI 主进程与后台管理逻辑强耦合

## 计划任务设计

计划任务必须直接调用发布产物，而不是调用仓库内 PowerShell 脚本。

推荐执行目标：

```text
%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe run-once --headless
```

### 安装流程

1. 用户在 GUI 中点击安装或重装
2. 程序确认当前发布版 `.exe` 已复制到稳定安装路径
3. 注册计划任务
4. 任务按设定间隔调用 `run-once --headless`
5. headless 模式写日志到本地日志目录

### 首版计划任务配置

- 任务名
  - 默认：`CodexSubMcpWatchdog`
- 巡检间隔
  - 默认：10 分钟
- 当前用户任务
- 开机 / 登录后有效
- 后台无窗口执行

### 为什么需要稳定安装路径

用户可能直接从 `Downloads` 双击 Release 中的 `.exe`。如果计划任务直接绑定下载目录中的文件，移动或删除该文件后任务就会失效。因此安装流程必须先把 `.exe` 放到稳定位置，再注册任务。

## GUI 信息架构

GUI 推荐采用：

- 左侧导航
- 顶部状态条
- 主工作区
- 底部日志抽屉

页面分为六个主视图：

- `总览`
- `清理`
- `计划任务`
- `配置`
- `MCP 检索`
- `日志`

### 总览

显示：

- 计划任务状态
- 当前配置摘要
- 最近一次扫描结果
- MCP 检索摘要

提供快捷操作：

- `立即预览`
- `立即清理`
- `安装/重装任务`
- `扫描 MCP`

### 清理

展示候选 suites 表格与详情面板。

表格重点字段：

- suite id
- 分类
- root pid
- 进程数
- 创建时间
- 是否会被清理

详情面板展示：

- 进程树
- 命令行摘要
- 判定原因
- 风险提示

### 计划任务

展示：

- 是否已安装
- 是否启用
- 巡检间隔
- 下次运行时间
- 稳定安装路径

提供动作：

- 安装
- 重装
- 卸载
- 启用
- 禁用
- 立即执行一次

### 配置

双模式编辑：

- 表单模式
  - 适合基础字段
- JSON 模式
  - 适合高级规则

支持：

- 恢复默认
- 导入
- 导出
- 配置校验

### MCP 检索

以两个 Tab 分开展示：

- 已配置可用的 MCP
- 疑似已安装但未配置的 MCP

每条结果至少展示：

- 名称
- 来源
- 路径或命令
- 版本
- 置信度
- 备注

### 日志

支持：

- 查看运行记录
- 查看详细输出
- 按动作类型与状态过滤
- 导出日志
- 打开日志目录

## GUI 交互原则

- 长耗时操作必须异步执行，避免阻塞主线程
- 所有需要破坏性写操作的功能都应先预览再确认
- 需要管理员权限的按钮必须显式标识
- 全局保留日志抽屉，便于快速定位失败原因
- 表格数据支持复制与导出
- 默认不在 GUI 启动时执行真实清理

## MCP 检索模型

建议定义统一记录模型：

- `name`
- `category`
  - `configured`
  - `installed_candidate`
- `source`
  - `codex_config`
  - `cursor_config`
  - `claude_config`
  - `npm_global`
  - `python_env`
  - `path_executable`
- `command`
- `path`
- `version`
- `confidence`
  - `high`
  - `medium`
  - `low`
- `notes`

### 第一层：已配置可用的 MCP

数据来源：

- 已知 AI 工具配置文件
- 配置中的 MCP server 声明

校验逻辑：

- 解析名称、命令、参数和路径
- 尝试确认命令或路径是否存在
- 可执行性通过后可记为 `high`

### 第二层：疑似已安装但未配置的 MCP

扫描来源：

- `npm -g list --depth=0 --json`
- Python 环境中已安装的相关包或入口点
- PATH 中符合命名规则的可执行文件
- 已知常见模式：
  - `mcp-*`
  - `*mcp*`
  - `@modelcontextprotocol/*`
  - `agentation-mcp`
  - `mcp-server-fetch`

这层结果的定位是“高置信度候选”，不是绝对完整清单。

### 展示要求

- 两层结果必须分开展示
- 必须展示来源与置信度
- 不应把“已配置”与“疑似已安装”混成一个列表

## 代码迁移策略

当前仓库中的脚本应逐步重构，而不是一次性废弃：

- 保留 `cleanup_codex_mcp_orphans.py` 的核心识别逻辑
- 将套件聚类、清理策略、配置读写抽到 `core`
- 将计划任务与路径管理抽到 `platform/windows`
- 将新后台命令集中到统一 CLI 入口
- 现有 `tools/*.ps1` 可以暂时保留为兼容入口，但 README 的主入口应逐步转向 GUI / EXE

## 测试策略

建议分四层测试：

- `core` 单元测试
  - suite 聚类
  - 清理选择
  - 配置校验
  - MCP 记录建模
- `platform` 单元测试
  - Windows 路径解析
  - 任务命令生成
  - 提权参数拼装
- `cli` 集成测试
  - `--help`
  - `task status`
  - `scan mcp --format json`
- `gui` 烟雾测试
  - 主窗口可启动
  - 页面能切换
  - 基础状态可加载

### 验证边界

涉及计划任务安装、真实进程清理和 UAC 的行为，首版以：

- 自动化 mock 测试
- 本机手工验证清单

相结合，不将全部系统级行为强行塞入全自动测试。

## Release 打包策略

目标产物：

- `CodexSubMcpManager-windows-x64.exe`

可选附加文件：

- `checksums.txt`
- `README-release.md`

建议打包方式：

- `PyInstaller --onefile --windowed`
- 在 GitHub Actions 的 Windows runner 上打包
- 通过 tag 触发 Release 草稿并上传产物

### 首版不做的事

- 不先做安装器
- 不先做自动更新
- 不先做代码签名

这些可以在 GUI 和打包链稳定后再迭代。

## 风险与权衡

- `PySide6 + PyInstaller --onefile` 的包体较大，但这是可接受代价
- 单文件程序首次启动可能略慢
- MCP 安装来源没有统一注册中心，因此第二层检索只能做到高置信度发现
- 如果 GUI 直接持有业务逻辑，后续计划任务和 headless 模式会产生重复实现
- 如果计划任务不绑定稳定路径，用户移动下载文件后会造成定时任务失效

## 验收标准

当以下条件满足时，可视为本设计完成：

- 能产出单文件 Windows `.exe`
- 无 Python 环境的机器可直接启动 GUI
- GUI 能执行 dry-run 与真实清理
- GUI 能安装、卸载、重装、启停计划任务
- GUI 能编辑并校验完整配置
- GUI 能展示双层 MCP 检索结果
- 计划任务直接调用发布版 `.exe`
- 所有运行态数据写入 `%LOCALAPPDATA%\CodexSubMcpManager\`
- 能在 GitHub Release 中发布可下载产物

## 结论

本设计将当前仓库从“源码脚本工具”演进为“可分发的 Windows 桌面管理器”。

核心方向是：

- 保留 Python 核心逻辑
- 以 `PySide6` 构建 GUI
- 以统一 CLI 承担后台命令面
- 以 `PyInstaller` 发布单文件 `.exe`
- 以 `%LOCALAPPDATA%` 承载运行时状态
- 以稳定安装路径支撑计划任务

这为下一阶段的实现计划提供了清晰边界：

- 先抽离核心逻辑与 CLI
- 再搭 GUI 壳与后台任务桥接
- 最后补打包链、Release 和手工验证清单
