# Release 发布流程

本仓库提供一个本地 PowerShell 发布脚本，用于在 Windows 上稳定生成并发布 Release 附件。

它的目标是解决一个实践中已经出现过的问题：

- 直接使用 `gh release upload` 上传较大的 `CodexSubMcpManager.exe` 时，可能出现长时间卡住、只生成 `starter` 资产或连接被重置

因此，本地脚本会使用：

- clean PyInstaller 构建
- GitHub Release API 创建 / 重建 release
- `curl.exe` 直传二进制附件
- 上传后回下载并校验 `SHA256`

## 前置条件

- Windows
- PowerShell 7+
- 已安装并登录 `gh`
- 可用的 `curl.exe`
- 本地仓库已存在目标 tag，并且 tag 已 push 到远端
- `venv` 已安装开发依赖，或系统 Python 能运行 `pytest` / `PyInstaller`

## 典型命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/publish-release.ps1 `
  -Tag v0.3.0 `
  -Title "v0.3.0 - Cleanup Redesign" `
  -NotesFile docs/release-notes/2026-03-28-v0.3.0-cleanup-redesign.md `
  -ReplaceExistingRelease
```

## 脚本会做什么

1. 校验 `gh`、`curl.exe`、git 运行环境
2. 校验 release note 文件存在
3. 校验本地 / 远端 tag 已存在
4. 执行 `pytest -q`
5. 用独立临时目录执行 clean PyInstaller 打包
6. 生成 `checksums.txt`
7. 按需删除旧 release（不删除 tag）
8. 通过 GitHub API 创建 release
9. 上传：
   - `CodexSubMcpManager.exe`
   - `checksums.txt`
10. 下载 release 附件并回验 `SHA256`

## 参数说明

- `-Tag`
  - 必填，例：`v0.3.0`
- `-Title`
  - 必填，例：`v0.3.0 - Cleanup Redesign`
- `-NotesFile`
  - 必填，release 正文文件
- `-Repository`
  - 可选，默认自动推断当前仓库
- `-ReplaceExistingRelease`
  - 可选。若目标 release 已存在，允许先删除旧 release 再重建
- `-SkipTests`
  - 可选。跳过 `pytest -q`

## 为什么不直接用 `gh release upload`

本仓库已经实际遇到过以下情况：

- `.exe` 上传时长时间卡住
- GitHub 上只留下 `starter` 状态资产
- 连接被重置，导致 release 表面存在但附件不完整

脚本改用更稳的上传路径，并把“回下载校验 hash”作为最后一步，避免出现“以为发好了，实际上附件不完整”的情况。

## 失败时先看哪里

### 1. 上传卡住

优先检查：

- 当前网络是否能稳定访问 `uploads.github.com`
- 机器上是否有安全软件拦截大文件上传
- 是否仍有旧的 PowerShell / curl 上传进程没有退出

### 2. 本地 `dist` 文件被占用

脚本默认不依赖仓库根目录 `dist/` 作为构建输出，而是使用临时目录构建，避免 exe 被句柄占用导致覆盖失败。

### 3. release 已存在

如果你确定要重发同一个 tag：

- 追加 `-ReplaceExistingRelease`

注意：

- 这会删除旧 release
- 不会删除 git tag

## 维护建议

- 对外发布前，优先准备好：
  - `docs/release-notes/*.md`
  - `docs/release-announcements/*.md`
- 正式对外发送时，优先使用最终用户公告文案，而不是直接贴技术 release note
