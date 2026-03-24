from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXAMPLE_CONFIG = PROJECT_ROOT / "tools" / "codex_mcp_watchdog.example.json"
DEFAULT_RUNTIME_CONFIG = PROJECT_ROOT / "temp" / "codex_mcp_watchdog" / "config.json"
DEFAULT_CONFIG = {
    "task_name": "CodexSubMcpWatchdog",
    "interval_minutes": 10,
    "max_suites": 6,
    "suite_window_seconds": 15,
    "codex_patterns": ["codex.exe", "@openai/codex/bin/codex.js"],
    "candidate_patterns": [
        "@modelcontextprotocol/",
        "agentation-mcp",
        "mcp-server-fetch",
        "ace-tool",
        "auggie",
        "--mcp",
    ],
}


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    ppid: int
    name: str
    created_at: datetime
    command_line: str


@dataclass(frozen=True)
class ProcessSuite:
    suite_id: str
    classification: str
    created_at: datetime
    root_pid: int
    processes: tuple[ProcessInfo, ...]
    live_codex_pid: int | None = None

    @property
    def process_ids(self) -> list[int]:
        return [process.pid for process in self.processes]


def _text(process: ProcessInfo) -> str:
    return f"{process.name} {process.command_line}".lower()


def _matches_patterns(process: ProcessInfo, patterns: Sequence[str]) -> bool:
    haystack = _text(process)
    return any(pattern.lower() in haystack for pattern in patterns)


def _is_codex_process(process: ProcessInfo, config: dict[str, object]) -> bool:
    patterns = config.get("codex_patterns", DEFAULT_CONFIG["codex_patterns"])
    return _matches_patterns(process, patterns)


def _is_candidate_process(process: ProcessInfo, config: dict[str, object]) -> bool:
    patterns = config.get("candidate_patterns", DEFAULT_CONFIG["candidate_patterns"])
    return _matches_patterns(process, patterns)


def _walk_ancestors(
    process: ProcessInfo,
    process_map: dict[int, ProcessInfo],
) -> Iterable[ProcessInfo]:
    seen: set[int] = set()
    current = process
    while current.ppid in process_map and current.ppid not in seen:
        seen.add(current.ppid)
        current = process_map[current.ppid]
        yield current


def _classify_root(
    process: ProcessInfo,
    process_map: dict[int, ProcessInfo],
    config: dict[str, object],
) -> tuple[str, int | None]:
    for ancestor in _walk_ancestors(process, process_map):
        if _is_codex_process(ancestor, config):
            return "attached_to_live_codex", ancestor.pid
    return "orphaned_after_codex_exit", None


def _suite_members(
    root: ProcessInfo,
    children: dict[int, list[ProcessInfo]],
) -> tuple[ProcessInfo, ...]:
    ordered: list[ProcessInfo] = []
    stack = [root]
    while stack:
        current = stack.pop()
        ordered.append(current)
        stack.extend(reversed(children.get(current.pid, [])))
    return tuple(sorted(ordered, key=lambda item: (item.created_at, item.pid)))


def build_candidate_suites(
    processes: Sequence[ProcessInfo],
    *,
    suite_window_seconds: int,
    config: dict[str, object] | None = None,
) -> list[ProcessSuite]:
    config = {**DEFAULT_CONFIG, **(config or {})}
    process_map = {process.pid: process for process in processes}
    tree_children: dict[int, list[ProcessInfo]] = defaultdict(list)
    for process in processes:
        tree_children[process.ppid].append(process)

    seed_candidates = {
        process.pid: process
        for process in processes
        if _is_candidate_process(process, config)
    }
    candidate_map = dict(seed_candidates)
    stack = list(seed_candidates.values())
    while stack:
        current = stack.pop()
        for child in tree_children.get(current.pid, []):
            if child.pid in candidate_map or _is_codex_process(child, config):
                continue
            candidate_map[child.pid] = child
            stack.append(child)

    candidate_children: dict[int, list[ProcessInfo]] = defaultdict(list)
    for process in candidate_map.values():
        if process.ppid in candidate_map:
            candidate_children[process.ppid].append(process)

    roots = sorted(
        (
            process
            for process in candidate_map.values()
            if process.ppid not in candidate_map
        ),
        key=lambda item: (item.created_at, item.pid),
    )

    attached: dict[int, ProcessSuite] = {}
    orphan_suites: list[dict[str, object]] = []
    for root in roots:
        classification, live_codex_pid = _classify_root(root, process_map, config)
        members = _suite_members(root, candidate_children)
        if classification == "attached_to_live_codex" and live_codex_pid is not None:
            existing = attached.get(live_codex_pid)
            if existing is None:
                attached[live_codex_pid] = ProcessSuite(
                    suite_id=f"live-{live_codex_pid}",
                    classification=classification,
                    created_at=root.created_at,
                    root_pid=root.pid,
                    processes=members,
                    live_codex_pid=live_codex_pid,
                )
                continue
            merged = sorted(
                [*existing.processes, *members],
                key=lambda item: (item.created_at, item.pid),
            )
            attached[live_codex_pid] = ProcessSuite(
                suite_id=existing.suite_id,
                classification=existing.classification,
                created_at=min(existing.created_at, root.created_at),
                root_pid=min(existing.root_pid, root.pid),
                processes=tuple(merged),
                live_codex_pid=live_codex_pid,
            )
            continue

        if (
            orphan_suites
            and (root.created_at - orphan_suites[-1]["last_created_at"]).total_seconds()
            <= suite_window_seconds
        ):
            orphan_suites[-1]["roots"].append(root.pid)
            orphan_suites[-1]["members"].extend(members)
            orphan_suites[-1]["last_created_at"] = root.created_at
            continue

        orphan_suites.append(
            {
                "created_at": root.created_at,
                "last_created_at": root.created_at,
                "roots": [root.pid],
                "members": list(members),
            }
        )

    suites = [
        *(
            ProcessSuite(
                suite_id=suite.suite_id,
                classification=suite.classification,
                created_at=suite.created_at,
                root_pid=suite.root_pid,
                processes=suite.processes,
                live_codex_pid=suite.live_codex_pid,
            )
            for suite in attached.values()
        ),
        *(
            ProcessSuite(
                suite_id=f"orphan-{index}",
                classification="orphaned_after_codex_exit",
                created_at=item["created_at"],
                root_pid=item["roots"][0],
                processes=tuple(
                    sorted(
                        item["members"],
                        key=lambda member: (member.created_at, member.pid),
                    )
                ),
            )
            for index, item in enumerate(orphan_suites, start=1)
        ),
    ]
    return sorted(suites, key=lambda suite: (suite.created_at, suite.root_pid))


def select_cleanup_suites(
    suites: Sequence[ProcessSuite],
    *,
    max_suites: int,
) -> list[ProcessSuite]:
    surplus = max(0, len(suites) - max_suites)
    if surplus == 0:
        return []
    orphan_suites = [
        suite
        for suite in sorted(suites, key=lambda item: (item.created_at, item.root_pid))
        if suite.classification == "orphaned_after_codex_exit"
    ]
    return orphan_suites[:surplus]


def cleanup_suites(
    suites: Sequence[ProcessSuite],
    *,
    dry_run: bool,
    kill_runner: Callable[[int], None],
) -> list[str]:
    actions: list[str] = []
    for suite in suites:
        if dry_run:
            actions.append(f"dry-run pid={suite.root_pid} processes={len(suite.processes)}")
            continue
        kill_runner(suite.root_pid)
        actions.append(f"killed pid={suite.root_pid} processes={len(suite.processes)}")
    return actions


def _load_config(config_path: Path) -> dict[str, object]:
    merged = dict(DEFAULT_CONFIG)
    source = config_path if config_path.exists() else DEFAULT_EXAMPLE_CONFIG
    if source.exists():
        merged.update(json.loads(source.read_text(encoding="utf-8")))
    return merged


def _run_taskkill(pid: int) -> None:
    result = subprocess.run(
        ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"taskkill failed for {pid}")


def build_process_query_command() -> list[str]:
    query = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "Get-CimInstance Win32_Process | ForEach-Object { "
        "[PSCustomObject]@{ "
        "pid = [int]$_.ProcessId; "
        "ppid = [int]$_.ParentProcessId; "
        "name = [string]$_.Name; "
        "created_at = if ($_.CreationDate) { $_.CreationDate.ToString('o') } else { '' }; "
        "command_line = [string]$_.CommandLine } } | ConvertTo-Json -Compress"
    )
    return ["powershell.exe", "-NoProfile", "-Command", query]


def _load_windows_processes() -> list[ProcessInfo]:
    command = build_process_query_command()
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "无法读取 Windows 进程快照")
    payload = json.loads(result.stdout or "[]")
    rows = payload if isinstance(payload, list) else [payload]
    return [
        ProcessInfo(
            pid=int(row["pid"]),
            ppid=int(row["ppid"]),
            name=str(row.get("name") or ""),
            created_at=datetime.fromisoformat(row.get("created_at") or datetime.now().isoformat()),
            command_line=str(row.get("command_line") or ""),
        )
        for row in rows
    ]


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="清理 Codex subagent 泄漏的 MCP 孤儿套件")
    parser.add_argument("--config", type=Path, default=DEFAULT_RUNTIME_CONFIG, help="本地配置路径")
    parser.add_argument("--yes", action="store_true", help="真正执行清理；默认仅预览")
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    processes = _load_windows_processes()
    suites = build_candidate_suites(
        processes,
        suite_window_seconds=int(config["suite_window_seconds"]),
        config=config,
    )
    cleanup_targets = select_cleanup_suites(suites, max_suites=int(config["max_suites"]))
    actions = cleanup_suites(
        cleanup_targets,
        dry_run=not args.yes,
        kill_runner=_run_taskkill,
    )

    print(
        f"发现 {len(suites)} 套候选 MCP，其中需要清理 {len(cleanup_targets)} 套。"
    )
    for action in actions:
        print(f"- {action}")
    if not actions:
        print("未发现需要清理的超额孤儿套件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
