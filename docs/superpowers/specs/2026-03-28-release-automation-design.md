# Release Automation And Announcement Design

## 目标

为仓库补两项发布侧能力：

1. 一份可直接对外发送的最终用户公告文案
2. 一个可在 Windows 本地复用的 release 自动化脚本

## 范围

- 新增最终用户公告文档
- 新增本地 PowerShell 发布脚本
- 新增维护者发布流程说明
- 更新 README 中的发布文档索引
- 新增静态回归测试，确保脚本继续使用稳定上传方案

## 关键约束

- 不重构现有业务代码
- 不把本轮范围扩展到自动更新、安装器或代码签名
- 脚本必须覆盖“大 exe 上传失败或卡成 starter”的已知问题

## 方案

- 构建：继续使用 `PyInstaller`
- 上传：不直接依赖 `gh release upload` 处理大二进制
- 创建 release：用 GitHub API
- 上传资产：用 `curl.exe` 直传 upload API
- 验证：上传后回下载并校验 `SHA256`

## 产出

- `docs/release-announcements/2026-03-28-v0.3.0-end-user.md`
- `docs/release-process.md`
- `scripts/publish-release.ps1`
- `tests/test_release_publish_script.py`
