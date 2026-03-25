# CodexSubMcp GUI Release 手工验收清单

## 环境

- Windows 机器
- 一台无 Python 机器用于 Release 验收
- 如涉及计划任务安装与真实清理，允许弹出 UAC

## 启动与目录

- [ ] 双击 `CodexSubMcpManager.exe` 可正常打开 GUI
- [ ] 首次启动会生成 `%LOCALAPPDATA%\CodexSubMcpManager\config.json`
- [ ] `%LOCALAPPDATA%\CodexSubMcpManager\logs\` 会被创建
- [ ] `%LOCALAPPDATA%\CodexSubMcpManager\bin\` 会被创建

## GUI 基本功能

- [ ] `总览` 页面可打开
- [ ] `清理` 页面可打开
- [ ] `计划任务` 页面可打开
- [ ] `配置` 页面可打开
- [ ] `MCP 检索` 页面可打开
- [ ] `日志` 页面可打开

## 清理与日志

- [ ] 点击 `立即预览` 能生成 dry-run 结果
- [ ] `python -m codexsubmcp dry-run --headless` 能输出 JSON
- [ ] `python -m codexsubmcp run-once --headless` 能输出 JSON 并写入日志
- [ ] 如存在超额 orphan suite，真实清理后日志中能看到 `killed pid=...`

## 配置

- [ ] 配置页能加载当前 `config.json`
- [ ] 非法配置不会静默覆盖文件
- [ ] 修正配置后可以成功保存

## MCP 检索

- [ ] `scan mcp --format json` 顶层包含 `configured` 与 `installed_candidates`
- [ ] GUI 中可分开展示已配置 MCP 与疑似已安装 MCP
- [ ] `npm -g` 中存在 MCP 包时，能在候选列表里出现

## 计划任务

- [ ] 安装计划任务后，任务名为 `CodexSubMcpWatchdog`
- [ ] 任务动作直接指向 `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe`
- [ ] 任务参数包含 `run-once --headless`
- [ ] 卸载计划任务后，任务会被移除

## Release

- [ ] GitHub Actions 能在 tag push 后构建 `CodexSubMcpManager.exe`
- [ ] Release 附件包含 `.exe` 与 `checksums.txt`
- [ ] 无 Python 机器可直接运行 Release 中的 `.exe`
