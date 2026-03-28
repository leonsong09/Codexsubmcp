# Codex Upstream Windows stdio MCP Teardown Design

## Goal

面向 `openai/codex` 上游提交一个**首个可合并 PR**，以最小改动修复 **Windows 下 stdio MCP 生命周期结束后旧子进程树残留**的问题，并用两层测试证明修复同时覆盖工程级 teardown 缺口与 multi-agent / refresh 场景下的重复堆积症状。

本轮目标不是引入新的诊断命令，也不是改变“每个 subagent 可以拥有独立 MCP 实例”的现有设计，而是让**不再被使用的 stdio MCP 进程树能够被可靠回收**。

## Background

本地仓库 `CodexSubMcp` 已经验证并建模了如下事实：

1. Codex 当前 MCP 配置来源是 `CODEX_HOME/config.toml` 及项目 `.codex/config.toml`
2. Codex 当前线程 / subagent 生命周期会写入 `state_5.sqlite`
3. 在 Windows 上，多 agent / 多轮 refresh / subagent 关闭后，旧的 `cmd` / `npx` / `node` / `uvx` 分支可能继续挂在旧的 Codex 会话之下
4. 这些残留分支会形成：
   - 重复 stdio MCP launcher stacks
   - 内存与句柄持续占用
   - 长时间会话下的明显堆积

上游源码与 issue 进一步表明：

- `codex-rs/core/src/config_loader/mod.rs` 明确支持 `${CODEX_HOME}/config.toml` 与项目 `.codex/config.toml`
- `codex-rs/state/src/lib.rs` 与 `codex-rs/state/src/runtime.rs` 明确状态库版本为 `state_5.sqlite`
- `codex-rs/state/src/runtime/threads.rs` 维护 `thread_spawn_edges`
- `codex-rs/rmcp-client/src/rmcp_client.rs` 中：
  - `kill_on_drop(true)` 已存在
  - `process_group(0)` 仅在 `#[cfg(unix)]` 下生效
  - `ProcessGroupGuard` 在非 Unix 下为空实现
- 因此，Windows stdio MCP 当前更依赖 `kill_on_drop(true)` 的 best-effort 行为，而这对 `cmd -> npx -> node` 或更深的子孙进程链并不总是足够

## Relevant Upstream Issues / PRs

### Primary alignment

- `#12976` — Codex startup sub-agent will restart a bunch of mcp, but it will not be automatically cleared after closing the sub-agent.
- `#14233` — long-lived multi-agent sessions accumulate duplicate stdio MCP stacks instead of returning to a bounded baseline

### Important scope guard

- `#12333` — duplicate Serena MCP instances complaint, closed as `not planned`
  - maintainer comment indicates that **separate MCP instances for subagents can be by design** because subagents may use different MCP configurations

### Related symptoms

- `#14950` — stale MCP node helper trees from older sessions
- `#12491` — app GUI zombie / unreaped MCP child processes
- `#11324` — MCP servers eat up memory when multi-tasking
- `#7155` — Windows MCP transport / stderr-related failure, adjacent but not the same bug
- `#15395` — plugin-loaded MCP cleanup draft PR, useful signal that upstream accepts MCP cleanup work when narrowly scoped

## Non-Goals

本轮明确**不做**：

1. 不改变“每个 subagent 可以拥有独立 MCP 实例”的模型
2. 不做 MCP 共享池 / connection sharing / pooling
3. 不增加 `doctor` / `diagnostics` / `stale inventory` CLI 或 app-server 接口
4. 不改 `streamable_http` 传输生命周期
5. 不做 app / desktop 专属大改
6. 不把外部 watchdog 的 `stale branch heuristic` 直接搬入 core cleanup 逻辑

## Product / Review Positioning

这个 PR 的定位必须是：

> 修复 **Windows 下 stdio MCP 的生命周期 teardown 缺口**，而不是改变多 agent 设计。

也就是说，PR 文案不能声称“消除重复 MCP 实例”，而应明确表述为：

- unused / old stdio MCP process trees should be reaped reliably
- Windows lifecycle teardown should clean launcher descendants
- old stdio MCP launcher trees should not survive manager refresh / agent-session shutdown

## Recommended Approach Options

### Option A — Fix only `rmcp-client`

仅在 `codex-rs/rmcp-client/src/rmcp_client.rs` 内补 Windows stdio child-tree teardown。

**Pros**
- 范围集中
- 容易解释

**Cons**
- 难以证明 multi-agent / lifecycle 症状被真正覆盖
- reviewer 容易把它看作底层优化而不是用户问题修复

### Option B — Lifecycle fix first, minimum cross-layer support (**Recommended**)

- 在 `rmcp-client` 增加 Windows stdio MCP 子树可靠回收能力
- 在 `core` 生命周期替换路径上确保旧 manager / client 的释放真正触发 teardown
- 补两层测试：
  1. 低层 teardown regression
  2. 高层 symptom regression

**Pros**
- 最贴近真实问题
- 改动仍然较小
- 能同时回答“为什么修”和“怎样证明修好了”

**Cons**
- 需要跨 `rmcp-client` 与 `core`
- 测试设计要求更高

### Option C — Diagnostics + fix

在首个 PR 中同时加诊断入口与 teardown 修复。

**Pros**
- 用户可见收益更高

**Cons**
- PR 体积变大
- 更容易被要求拆分

## Chosen Design

采用 **Option B**。

### Core idea

不把本地仓库的 `stale branch` 推断模型搬进 upstream 核心逻辑，而是修正更根本的点：

> 在 Windows 上，把 stdio MCP teardown 从 `kill_on_drop(true)` 的 best effort，提升为对整个 launcher 子树的显式、可靠回收。

### Why this fits upstream

- 保持现有 subagent / MCP ownership 语义不变
- 不要求 reviewer 接受新的产品行为
- 只修复生命周期结束后“不该继续存在”的进程树
- 与现有 issue 的用户痛点直接一致

## Detailed Architecture

### Layer 1 — `codex-rs/rmcp-client/src/rmcp_client.rs`

这是首修点。

#### Current state

当前 stdio MCP 创建路径：

- 创建 `Command`
- `kill_on_drop(true)`
- Unix 下 `process_group(0)`
- spawn 后为 stderr 启一个 reader task
- 用 `ProcessGroupGuard` 在 Unix 下做 group terminate / kill
- Windows 下 `ProcessGroupGuard` 为空实现

#### Required change

为 stdio transport 增加 **Windows child-tree guard**，语义与 Unix `ProcessGroupGuard` 对齐：

- Unix：继续沿用现有 process group 逻辑
- Windows：记录 launcher PID，并在 teardown 时显式终止整棵子进程树

#### Implementation preference

优先选择：

- 在现有 utils 层新增或复用 **Windows process tree kill helper**
- 再由 `rmcp-client` 调用该 helper

不推荐把完整 Windows 平台逻辑直接散落在 `rmcp_client.rs`，除非上游现有工具层无法承载最小实现。

#### Behavioral requirement

当 stdio MCP client 被 drop、替换、或其 owning manager 被释放时：

- launcher 必须退出
- launcher 的 descendants 也必须退出
- 不能留下 `cmd` / `npx` / `node` / `uvx` 残留树

### Layer 2 — `codex-rs/core/src/mcp_connection_manager.rs`

这是第二修点。

#### Goal

确保这些路径中的旧 client 真正失去持有，从而触发 teardown：

1. session init 创建新 `McpConnectionManager`
2. refresh MCP servers 时替换旧 manager
3. 生命周期结束时释放 manager

#### Constraint

首个 PR 不重写 ownership 模型，不引入新的 ref-count 或 pooling 语义。

#### Required verification

需要通过测试证明：

- manager replace 后旧 stdio MCP 树退出
- refresh 之后不会留下前一轮旧 stdio launcher 分支

### Layer 3 — `codex-rs/core/src/agent/control.rs`

这里不作为首要改动点，但需要作为症状链路验证的一部分。

#### Current role

- `close_agent()` 会将 `thread_spawn_edges` 标记为 `Closed`
- `shutdown_live_agent()` / `shutdown_agent_tree()` 负责 agent lifecycle 关闭

#### Plan

首个 PR 中对该文件采取保守策略：

- 先补测试证明是否存在额外缺口
- 仅在测试显示 agent close 无法触发相关 teardown 时，才做最小修正

## Test Strategy

### Test Layer A — low-level teardown regression

**Goal:** 证明 Windows stdio MCP launcher + descendants 在 client / manager drop 后全部退出。

#### Suggested shape

- 准备一个 fake stdio MCP launcher
- launcher 再派生 child / grandchild
- 创建 `RmcpClient::new_stdio_client(...)`
- drop client 或替换 owning manager
- 断言 launcher / child / grandchild 全部结束

#### Key requirement

测试必须尽量事件驱动，避免高度依赖 sleep；如果必须等待，等待应短且可解释。

### Test Layer B — symptom-level regression

**Goal:** 证明 multi-agent / refresh / repeated lifecycle 场景下，不再持续累积旧 stdio MCP stacks。

#### Suggested shape

- 配置一个最小 stdio MCP
- 触发多轮 agent spawn / close 或 manager refresh
- 最终断言：
  - 要么回到 0
  - 要么回到 bounded baseline
  - 绝不能保留旧一轮 launcher trees

#### Important note

这个测试不要求完整复刻本地 watchdog 观测到的海量实例，只要稳定证明“旧实例不会被遗留”即可。

## Acceptance Criteria

首个 PR 通过标准同时满足以下两组条件：

### Engineering acceptance

1. Windows stdio MCP 在 client / manager lifecycle 结束后能可靠 teardown
2. 旧 launcher descendants 不会残留
3. 不影响 Unix 现有 process group cleanup 路径
4. 不改变 `streamable_http` 行为

### Symptom acceptance

1. 多轮 agent / refresh 后，stdio MCP stacks 不会单调累积
2. 关闭 agent / 替换 manager 后，旧 launcher 树最终消失
3. 回归测试能直接覆盖上述用户症状

## Submission Strategy

### Issue / PR sequence

采用“两步一起”的路径：

1. 先在现有相关 issue（首选 `#12976`）下发一个短 comment 对齐方案
2. 随后立刻提交 PR

### Comment message intent

comment 只做三件事：

- 声明不改变 subagent 独立 MCP 实例设计
- 声明只修 Windows stdio lifecycle teardown
- 说明 PR 会带低层 + 症状层两类测试

### Fork / branch

- fork: `leonsong09/codex`
- branch: `fix/windows-stdio-mcp-teardown`

### PR framing

PR 标题建议：

- `Fix Windows stdio MCP teardown across agent/session lifecycle`
- 或 `Ensure Windows stdio MCP processes are reaped on lifecycle shutdown`

PR 摘要必须强调：

- does not change subagent MCP ownership design
- fixes Windows stdio teardown only
- adds low-level and symptom-level regression coverage

## Risks

### Risk 1 — Wrong Windows tree-kill primitive

如果选了上游 reviewer 不接受的 Windows kill-tree 实现，PR 容易卡住。

**Mitigation**
- 优先复用现有 utils 层
- 把平台逻辑封装在 helper 中，避免传播到业务层

### Risk 2 — Flaky symptom regression tests

multi-agent / lifecycle 场景容易受时序影响。

**Mitigation**
- 尽量使用事件驱动等待
- 将症状测试保持为“最小稳定场景”
- 不追求复刻完整现场规模

### Risk 3 — Reviewer误解为“要消除重复实例”

这会撞上 `#12333` 的既有结论。

**Mitigation**
- issue comment 与 PR 文案反复声明：
  - separate instances may still exist by design
  - only unused / stale process trees should be reaped

## Out of Scope Follow-ups

这些内容放入后续 issue / PR，而不进入首个 PR：

1. `configured / running / drift / stale` 诊断命令
2. 基于 `state_5.sqlite + process tree` 的内建审计工具
3. 自动 orphan cleanup 策略
4. streamable_http 生命周期统一观察接口
5. 面向 app-server / desktop 的诊断 UI

## Proposed Execution Order

1. 创建 fork 并添加远端
2. 在 `#12976` 发方案 comment
3. 新建分支 `fix/windows-stdio-mcp-teardown`
4. 先写失败测试：
   - low-level teardown
   - symptom-level accumulation
5. 再补 Windows stdio MCP tree teardown 实现
6. 运行相关测试并收敛
7. push 到 fork
8. 发起 PR

## Definition of Success

如果最终 PR 能满足下面这句话，就算这轮成功：

> 在 Windows 上，即便 multi-agent / refresh 仍然会创建独立 stdio MCP 实例，只要这些实例不再被当前生命周期持有，它们的 launcher 子树就会被可靠回收，而不会继续堆积为 stale MCP branches。
