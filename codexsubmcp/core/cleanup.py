from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Sequence

from codexsubmcp.core.config import DEFAULT_CONFIG, validate_config
from codexsubmcp.core.models import CleanupReport, ProcessInfo, ProcessSuite


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
    config = validate_config({**DEFAULT_CONFIG, **(config or {}), "suite_window_seconds": suite_window_seconds})
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


def run_cleanup(
    processes: Sequence[ProcessInfo],
    *,
    config: dict[str, object],
    dry_run: bool,
    kill_runner: Callable[[int], None],
) -> CleanupReport:
    merged_config = validate_config({**DEFAULT_CONFIG, **config})
    suites = build_candidate_suites(
        processes,
        suite_window_seconds=int(merged_config["suite_window_seconds"]),
        config=merged_config,
    )
    cleanup_targets = select_cleanup_suites(
        suites,
        max_suites=int(merged_config["max_suites"]),
    )
    actions = cleanup_suites(cleanup_targets, dry_run=dry_run, kill_runner=kill_runner)
    return CleanupReport(
        suites=tuple(suites),
        cleanup_targets=tuple(cleanup_targets),
        actions=actions,
    )
