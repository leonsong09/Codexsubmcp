# CodexSubMcp GUI Release 手工验收清单

## 环境

- [ ] Windows 机器 1 台
- [ ] 无 Python 机器 1 台，用于 Release 最终验收
- [ ] 当前用户可接受 UAC 弹窗
- [ ] 如需验证真实清理，准备一组可复现的 orphan MCP 进程

## 启动与目录

- [ ] 双击 `CodexSubMcpManager.exe` 可正常启动 GUI
- [ ] 首次启动后生成 `%LOCALAPPDATA%\CodexSubMcpManager\config.json`
- [ ] 首次启动后生成 `%LOCALAPPDATA%\CodexSubMcpManager\logs\`
- [ ] 首次启动后生成 `%LOCALAPPDATA%\CodexSubMcpManager\cache\`
- [ ] 首次启动后生成 `%LOCALAPPDATA%\CodexSubMcpManager\exports\`
- [ ] 首次启动后生成 `%LOCALAPPDATA%\CodexSubMcpManager\bin\`

## 主框架

- [ ] 左侧导航包含 `总览 / 计划任务 / 配置 / 日志`
- [ ] 顶部状态条可见，能显示当前页面、任务状态、活动状态、日志目录

## 总览页

- [ ] 总览页能显示计划任务摘要
- [ ] 总览页能显示配置摘要
- [ ] 总览页能显示 MCP 摘要
- [ ] 总览页能显示最近刷新状态、识别校验状态、当前运行态、最近清理结果、累计统计
- [ ] 总览页的 `刷新` 会触发识别校验与 orphan 结果生成
- [ ] 总览页的 `执行清理（管理员）` 会触发管理员清理链路
- [ ] 总览中的清理结果表格可展示 orphan 目标
- [ ] 表格列包含 `Target / 类型 / Kill PID / 进程数 / 创建时间 / 动作`
- [ ] 详情面板能展示：
  - [ ] 判定原因
  - [ ] 风险提示
- [ ] 点击 `复制结果` 后，剪贴板中包含表格头和 target 数据
- [ ] 点击 `导出结果` 后，`%LOCALAPPDATA%\CodexSubMcpManager\exports\cleanup-targets.tsv` 会生成
- [ ] 非管理员状态点击 `立即清理（管理员）` 时会弹出 UAC
- [ ] 管理员确认后，如存在 orphan suite，详情和摘要中能看到真实清理结果
- [ ] 管理员拒绝或执行失败时，顶部活动状态会记录失败

## 计划任务页

- [ ] 页面可显示：
  - [ ] 是否已安装
  - [ ] 是否启用
  - [ ] 巡检间隔
  - [ ] 下次运行时间
  - [ ] 稳定安装路径
  - [ ] 参数
- [ ] `安装（管理员）` 在非管理员状态下会弹 UAC
- [ ] `重装（管理员）` 在非管理员状态下会弹 UAC
- [ ] `卸载（管理员）` 在非管理员状态下会弹 UAC
- [ ] `启用（管理员）` 在非管理员状态下会弹 UAC
- [ ] `禁用（管理员）` 在非管理员状态下会弹 UAC
- [ ] 安装后任务名为 `CodexSubMcpWatchdog`
- [ ] 任务动作指向 `%LOCALAPPDATA%\CodexSubMcpManager\bin\CodexSubMcpManager.exe`
- [ ] 任务参数包含 `run-once --headless`
- [ ] GUI 刷新后能回显实际巡检间隔和下次运行时间
- [ ] `立即执行一次` 可以直接触发一次清理流程

## 配置页

- [ ] 配置页存在 `表单` 与 `JSON` 两个 Tab
- [ ] 表单模式可编辑基础字段：
  - [ ] 任务名
  - [ ] 巡检间隔
  - [ ] 最大套件数
  - [ ] 聚类窗口秒数
  - [ ] Codex Patterns
  - [ ] Candidate Patterns
- [ ] 从表单切到 JSON 时，内容会同步
- [ ] 从 JSON 切回表单时，字段会同步
- [ ] 非法配置不会静默覆盖 `config.json`
- [ ] `校验配置` 会给出有效或错误提示
- [ ] `恢复默认` 会恢复默认配置
- [ ] `导入配置` 可载入外部 JSON
- [ ] `导出配置` 可导出到选定路径
- [ ] `保存配置` 后 `config.json` 实际落盘

## 总览中的 MCP 检索面板

- [ ] 面板存在两个 Tab：
  - [ ] `已配置`
  - [ ] `运行中`
- [ ] 列表项会显示名称、来源、版本/置信度，以及路径或命令摘要
- [ ] 点击记录后，详情面板能显示：
  - [ ] `name`
  - [ ] `source`
  - [ ] `command`
  - [ ] `path`
- [ ] `复制结果` 会把当前 inventory JSON 放入剪贴板
- [ ] `导出结果` 会生成 `%LOCALAPPDATA%\CodexSubMcpManager\exports\mcp-inventory.json`
- [ ] `scan mcp --format json` 输出顶层包含 `configured / running / drift`

## 日志页

- [ ] 日志页能列出 `%LOCALAPPDATA%\CodexSubMcpManager\logs\` 中的日志
- [ ] 选择日志后可查看详细内容
- [ ] `动作` 过滤可筛选 `dry-run / cleanup / run-once`
- [ ] `状态` 过滤可筛选 `success / failure`
- [ ] `导出当前日志` 能复制当前文件到 `%LOCALAPPDATA%\CodexSubMcpManager\exports\`
- [ ] `打开日志目录` 能打开本地日志目录

## CLI 与 headless

- [ ] `CodexSubMcpManager.exe dry-run --headless` 输出 JSON
- [ ] `CodexSubMcpManager.exe cleanup --yes --headless` 输出 JSON
- [ ] `CodexSubMcpManager.exe cleanup --yes --headless --report-file <path>` 会额外生成报告文件
- [ ] `CodexSubMcpManager.exe run-once --headless` 输出 JSON 并写入日志
- [ ] `CodexSubMcpManager.exe task status --format json` 输出结构化状态

## Release

- [ ] GitHub Actions 能构建 `CodexSubMcpManager.exe`
- [ ] Release 附件包含 `.exe`
- [ ] 如有 `checksums.txt`，校验值与产物一致
- [ ] 无 Python 机器可直接运行 Release 中的 `.exe`
- [ ] 无 Python 机器上的计划任务安装、启用、禁用、卸载均可完成
