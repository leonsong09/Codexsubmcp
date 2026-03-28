from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from codexsubmcp.core.models import McpRecord, ProcessInfo, ProcessSuite


@dataclass(frozen=True)
class AttachedBranch:
    tool_signature: str
    launcher_pid: int
    created_at: datetime
    processes: tuple[ProcessInfo, ...]

    @property
    def process_ids(self) -> list[int]:
        return [process.pid for process in self.processes]


@dataclass(frozen=True)
class StaleAttachedBranch:
    tool_signature: str
    live_codex_pid: int
    launcher_pid: int
    latest_kept_launcher_pid: int
    created_at: datetime
    processes: tuple[ProcessInfo, ...]

    @property
    def process_ids(self) -> list[int]:
        return [process.pid for process in self.processes]


def infer_tool_signature(command_line: str) -> str:
    lowered = command_line.lower()
    patterns = (
        ("chrome-devtools-mcp", "chrome-devtools-mcp"),
        ("chrome_devtools", "chrome-devtools-mcp"),
        ("@playwright/mcp", "playwright-mcp"),
        ("ace-tool", "ace-tool"),
        ("agentation-mcp", "agentation-mcp"),
        ("@modelcontextprotocol/server-memory", "server-memory"),
        ("server-memory", "server-memory"),
        ("@modelcontextprotocol/server-sequential-thinking", "server-sequential-thinking"),
        ("server-sequential-thinking", "server-sequential-thinking"),
        ("mcp-server-fetch", "mcp-server-fetch"),
    )
    for needle, signature in patterns:
        if needle in lowered:
            return signature
    return lowered.strip() or "unknown"


def infer_record_tool_signature(record: McpRecord) -> str:
    haystack = " ".join([record.name, record.command or "", *record.args]).strip()
    return infer_tool_signature(haystack)


def _branch_processes(
    launcher: ProcessInfo,
    children: dict[int, list[ProcessInfo]],
) -> tuple[ProcessInfo, ...]:
    seen: set[int] = set()
    stack = [launcher]
    branch: list[ProcessInfo] = []
    while stack:
        process = stack.pop()
        if process.pid in seen:
            continue
        seen.add(process.pid)
        branch.append(process)
        stack.extend(reversed(children.get(process.pid, [])))
    return tuple(sorted(branch, key=lambda item: (item.created_at, item.pid)))


def build_attached_branches(suite: ProcessSuite) -> list[AttachedBranch]:
    if suite.classification != "attached_to_live_codex" or suite.live_codex_pid is None:
        return []
    children: dict[int, list[ProcessInfo]] = defaultdict(list)
    for process in suite.processes:
        children[process.ppid].append(process)
    launchers = [process for process in suite.processes if process.ppid == suite.live_codex_pid]
    branches = [
        AttachedBranch(
            tool_signature=infer_tool_signature(launcher.command_line),
            launcher_pid=launcher.pid,
            created_at=launcher.created_at,
            processes=_branch_processes(launcher, children),
        )
        for launcher in sorted(launchers, key=lambda item: (item.created_at, item.pid))
    ]
    return branches


def find_stale_attached_branches(suite: ProcessSuite) -> list[StaleAttachedBranch]:
    if suite.live_codex_pid is None:
        return []
    grouped: dict[str, list[AttachedBranch]] = defaultdict(list)
    for branch in build_attached_branches(suite):
        grouped[branch.tool_signature].append(branch)
    stale: list[StaleAttachedBranch] = []
    for branches in grouped.values():
        if len(branches) <= 1:
            continue
        ordered = sorted(branches, key=lambda item: (item.created_at, item.launcher_pid))
        latest = ordered[-1]
        stale.extend(
            StaleAttachedBranch(
                tool_signature=branch.tool_signature,
                live_codex_pid=suite.live_codex_pid,
                launcher_pid=branch.launcher_pid,
                latest_kept_launcher_pid=latest.launcher_pid,
                created_at=branch.created_at,
                processes=branch.processes,
            )
            for branch in ordered[:-1]
        )
    return sorted(stale, key=lambda item: (item.created_at, item.launcher_pid))
