# Release Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为仓库补最终用户公告与可复用的本地 Windows release 自动化脚本。

**Architecture:** 文档侧新增“对外公告”和“维护者发布流程”，脚本侧新增一个独立 PowerShell 发布入口，使用 clean build + GitHub API + curl 上传 + 回下载 hash 校验，避免大 exe 上传半成品问题。

**Tech Stack:** PowerShell 7, git, GitHub CLI, curl.exe, PyInstaller, pytest

---

### Task 1: 补最终用户公告

**Files:**
- Create: `docs/release-announcements/2026-03-28-v0.3.0-end-user.md`

- [ ] 写最终用户视角文案
- [ ] 覆盖：适用人群、升级价值、如何开始使用、下载入口

### Task 2: 补本地发布脚本

**Files:**
- Create: `scripts/publish-release.ps1`

- [ ] 增加参数：`Tag / Title / NotesFile`
- [ ] 增加 release 重建开关
- [ ] 增加 clean build、checksum、API 创建 release、curl 上传、回下载校验

### Task 3: 补维护者说明与回归测试

**Files:**
- Create: `docs/release-process.md`
- Modify: `README.md`
- Create: `tests/test_release_publish_script.py`

- [ ] 在 README 中补最新 release 文档入口
- [ ] 为脚本关键上传路径增加静态回归测试
- [ ] 跑定向 pytest 验证
