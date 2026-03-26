# v0.2.0 - CodexSubMcpManager GUI 对齐版

本版本把 CodexSubMcp 收口为可发布的 Windows GUI 管理器，适合直接放到 GitHub Release 给无 Python 环境的机器使用。

## 主要更新

- 新增统一 GUI 主框架：
  - 左侧导航
  - 顶部状态条
  - 底部活动抽屉
  - 统一主题与按钮层级
- 补齐六个页面：
  - 总览
  - 清理
  - 计划任务
  - 配置
  - MCP 检索
  - 日志
- 补齐关键交互：
  - 清理结果详情、复制、导出
  - 配置页表单 / JSON 双模式
  - MCP 双 Tab、详情、复制、导出
  - 日志过滤、导出、打开目录
- 补齐管理员动作链路：
  - 计划任务管理按需提权
  - 真实清理按需提权
  - 清理结果结构化回传 GUI

## 运行时目录

- `%LOCALAPPDATA%\CodexSubMcpManager\config.json`
- `%LOCALAPPDATA%\CodexSubMcpManager\logs\`
- `%LOCALAPPDATA%\CodexSubMcpManager\cache\`
- `%LOCALAPPDATA%\CodexSubMcpManager\exports\`
- `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe`

## 验证

- `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui_smoke.py -q`
- `QT_QPA_PLATFORM=offscreen python -m pytest -q`
- `pyinstaller packaging/windows/CodexSubMcpManager.spec --noconfirm`

## 手工验收

- `docs/manual-validation/2026-03-25-codexsubmcp-gui-release-checklist.md`

## 已知说明

- MCP 候选扫描是高置信度发现，不承诺 100% 穷举
- UAC 真机链路仍建议在无 Python 机器上做一轮完整人工验收
