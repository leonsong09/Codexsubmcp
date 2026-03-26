# CodexSubMcpManager GUI 对齐版 Release 文案

## 建议 Tag

- `v0.2.0`

## 建议标题

- `v0.2.0 - CodexSubMcpManager GUI 对齐版`

## Release 正文

本版本将 CodexSubMcp 从脚本集合进一步收口为可发布的 Windows GUI 管理器，重点补齐了桌面管理端的一致性、可视化信息架构、计划任务管理、MCP 检索、日志管理与管理员动作链路。

### 本次更新

- 新增统一 GUI 主框架：
  - 左侧导航
  - 顶部状态条
  - 底部活动抽屉
  - 应用级深色主题与统一按钮层级
- 补齐总览页：
  - 计划任务摘要
  - 配置摘要
  - 最近清理摘要
  - MCP 摘要
  - 快捷操作入口
- 补齐清理页：
  - suites 表格
  - 详情面板
  - 判定原因
  - 风险提示
  - 进程树
  - 命令摘要
  - 复制结果
  - 导出结果
- 补齐计划任务页：
  - 安装 / 重装 / 卸载 / 启用 / 禁用 / 立即执行一次
  - 巡检间隔
  - 下次运行时间
  - 稳定安装路径
  - 参数展示
- 补齐配置页：
  - 表单模式
  - JSON 模式
  - 双向同步
  - 校验 / 恢复默认 / 导入 / 导出 / 保存
  - legacy 源码版配置迁移入口可继续补充
- 补齐 MCP 检索页：
  - 已配置可用 / 疑似已安装 双 Tab
  - 列表摘要
  - 详情面板
  - 复制结果
  - 导出结果
- 补齐日志页：
  - 动作过滤
  - 状态过滤
  - 日志导出
  - 打开日志目录
- 补齐按需提权：
  - 计划任务管理动作在非管理员场景下通过同一入口的管理员子命令执行
  - 真实清理在非管理员场景下通过管理员子命令执行，并通过结构化报告回传 GUI

### 运行时目录

- `%LOCALAPPDATA%\CodexSubMcpManager\config.json`
- `%LOCALAPPDATA%\CodexSubMcpManager\logs\`
- `%LOCALAPPDATA%\CodexSubMcpManager\cache\`
- `%LOCALAPPDATA%\CodexSubMcpManager\exports\`
- `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe`

### 验证结果

- `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui_smoke.py -q`
  - `35 passed`
- `QT_QPA_PLATFORM=offscreen python -m pytest -q`
  - `75 passed`
- `pyinstaller packaging/windows/CodexSubMcpManager.spec --noconfirm`
  - 构建成功

### 手工验收

请按以下清单执行：

- `docs/manual-validation/2026-03-25-codexsubmcp-gui-release-checklist.md`

### 已知剩余项

- legacy 源码版配置的自动发现导入还可继续补强
- UAC 真机链路仍建议在无 Python 机器上做一轮完整人工验收
- 界面视觉还可以继续细化，但当前功能链路已基本闭合

## 建议提交信息

- `✨ feat(gui): 完成发布版管理器界面对齐`

## 建议提交正文

本次提交将 CodexSubMcp 的发布版 GUI 收口为可交付状态。

- 补齐总览、清理、计划任务、配置、MCP、日志六个页面
- 补齐顶部状态条、底部活动抽屉与统一主题
- 为计划任务管理和真实清理补齐按需提权链路
- 为清理页和 MCP 页补齐复制与导出能力
- 为配置页补齐表单 / JSON 双模式与导入导出
- 更新手工验收清单并补齐自动化测试覆盖
