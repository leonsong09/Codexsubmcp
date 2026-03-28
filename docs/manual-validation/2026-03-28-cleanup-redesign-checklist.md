# 2026-03-28 Cleanup Redesign 手工验收清单

## 目标

验证 CodexSubMcp 已完成以下主流程重构：

- 刷新
- 预览
- 清理
- 日志回放

并确认 stale MCP branch 清理能力、累计统计、MCP 当前态展示均符合预期。

## 前置条件

1. Windows 环境
2. 能启动 GUI：

```powershell
CodexSubMcpManager.exe gui
```

3. 本机存在 Codex 运行目录：
   - `~/.codex/config.toml`
   - `~/.codex/state_5.sqlite`

## 验收项

### A. Refresh 当前态

- [ ] 打开 GUI 后，`总览` 页默认只允许点击 `刷新`
- [ ] 未刷新前，`预览清理` / `执行清理` 为禁用态
- [ ] 点击 `刷新` 后，总览页出现：
  - [ ] 运行中子代理数
  - [ ] 运行中 suite 数
  - [ ] 运行中 MCP 实例数
  - [ ] 已配置 MCP 数
  - [ ] 可清理目标数
- [ ] 总览页显示最近 refresh 的 `snapshot_id` 与时间
- [ ] `MCP 检索` 页同步更新 configured / running / drift
- [ ] `日志` 页新增一条 refresh 日志

### B. Preview 清理目标

- [ ] 点击 `预览清理`
- [ ] `清理` 页显示 preview summary
- [ ] `清理` 页表格展示 target，而不是旧 suite 列表
- [ ] 若存在 orphan target，可看到 `orphan_suite`
- [ ] 若存在 stale target，可看到 `stale_attached_branch`
- [ ] stale target 详情包含：
  - [ ] `tool_signature`
  - [ ] `latest_kept_launcher_pid`
- [ ] `日志` 页新增 preview 日志

### C. Cleanup 执行

- [ ] 点击 `执行清理`
- [ ] 如当前用户非管理员，应触发提权执行
- [ ] cleanup 完成后出现 cleanup 结果摘要
- [ ] cleanup 成功后自动再次 refresh
- [ ] 总览页最近 cleanup 摘要更新
- [ ] `日志` 页新增 cleanup 日志

### D. Lifetime Stats

- [ ] 总览页显示累计清理统计
- [ ] 仅成功 cleanup 会增加累计：
  - [ ] total cleanup count
  - [ ] total closed suite count
  - [ ] total closed stale branch count
  - [ ] total killed MCP instance count
  - [ ] total killed process count
- [ ] refresh / preview 不会污染上述累计统计

### E. MCP Diagnostic Page

- [ ] MCP 页不再出现 installed candidates 视图
- [ ] Configured tab 展示：
  - [ ] source
  - [ ] command
  - [ ] env_keys
  - [ ] timeout 信息
- [ ] Running tab 展示：
  - [ ] tool_signature
  - [ ] instance_count
  - [ ] live_codex_pid_count
  - [ ] has_stale
- [ ] drift 区域能显示：
  - [ ] configured_not_running
  - [ ] running_not_configured

### F. Log Replay

- [ ] Log list 能区分：
  - [ ] refresh
  - [ ] preview
  - [ ] cleanup
- [ ] cleanup 日志摘要包含：
  - [ ] `+suite`
  - [ ] `+stale`
  - [ ] `+MCP`
  - [ ] `+process`
- [ ] refresh 日志摘要包含当前态
- [ ] 点选日志后，详情面板显示完整 JSON
- [ ] 能导出当前日志
- [ ] 能打开日志目录

## 建议记录

验收时建议记录：

- 实测截图
- refresh / preview / cleanup 各 1 份日志样本
- 若存在 stale branch，被清理前后的进程对比

## 当前自动化验证参考

```powershell
pytest -q
```

当前结果：

- `107 passed`
