from __future__ import annotations

from datetime import datetime

from tools.cleanup_codex_mcp_orphans import (
    ProcessInfo,
    build_process_query_command,
    build_candidate_suites,
    cleanup_suites,
    select_cleanup_suites,
)


def _proc(
    pid: int,
    ppid: int,
    name: str,
    created_at: str,
    command_line: str,
) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        name=name,
        created_at=datetime.fromisoformat(created_at),
        command_line=command_line,
    )


def test_build_candidate_suites_marks_live_codex_and_orphans():
    processes = [
        _proc(100, 1, "codex.exe", "2026-03-24T10:00:00", r"C:\tool\codex.exe"),
        _proc(110, 100, "node.exe", "2026-03-24T10:00:01", "npx @modelcontextprotocol/server-memory"),
        _proc(111, 110, "node.exe", "2026-03-24T10:00:02", "node server-memory"),
        _proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "npx @modelcontextprotocol/server-sequential-thinking"),
        _proc(211, 210, "node.exe", "2026-03-24T09:00:01", "node server-sequential-thinking"),
    ]

    suites = build_candidate_suites(processes, suite_window_seconds=15)

    assert len(suites) == 2
    assert suites[0].classification == "orphaned_after_codex_exit"
    assert suites[0].process_ids == [210, 211]
    assert suites[1].classification == "attached_to_live_codex"
    assert suites[1].live_codex_pid == 100
    assert suites[1].process_ids == [110, 111]


def test_build_candidate_suites_groups_orphan_roots_within_time_window():
    processes = [
        _proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server"),
        _proc(211, 210, "node.exe", "2026-03-24T09:00:01", "node agentation-mcp"),
        _proc(220, 9998, "python.exe", "2026-03-24T09:00:08", "mcp-server-fetch.exe"),
        _proc(221, 220, "python.exe", "2026-03-24T09:00:09", "python mcp-server-fetch.exe"),
        _proc(310, 9997, "node.exe", "2026-03-24T09:05:00", "npx @modelcontextprotocol/server-memory"),
    ]

    suites = build_candidate_suites(processes, suite_window_seconds=15)

    assert len(suites) == 2
    assert suites[0].process_ids == [210, 211, 220, 221]
    assert suites[1].process_ids == [310]


def test_select_cleanup_suites_only_returns_oldest_excess_orphan_suites():
    processes = [
        _proc(100, 1, "codex.exe", "2026-03-24T10:00:00", r"C:\tool\codex.exe"),
        _proc(110, 100, "node.exe", "2026-03-24T10:00:01", "npx @modelcontextprotocol/server-memory"),
        _proc(210, 9999, "node.exe", "2026-03-24T08:00:00", "npx @modelcontextprotocol/server-sequential-thinking"),
        _proc(310, 9998, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server"),
    ]

    suites = build_candidate_suites(processes, suite_window_seconds=15)
    cleanup_targets = select_cleanup_suites(suites, max_suites=2)

    assert [suite.process_ids for suite in cleanup_targets] == [[210]]


def test_cleanup_suites_skips_kill_runner_in_dry_run():
    processes = [
        _proc(210, 9999, "node.exe", "2026-03-24T08:00:00", "npx @modelcontextprotocol/server-sequential-thinking"),
        _proc(211, 210, "node.exe", "2026-03-24T08:00:01", "node server-sequential-thinking"),
    ]
    suites = build_candidate_suites(processes, suite_window_seconds=15)
    seen: list[int] = []

    actions = cleanup_suites(
        suites,
        dry_run=True,
        kill_runner=lambda pid: seen.append(pid),
    )

    assert seen == []
    assert actions == ["dry-run pid=210 processes=2"]


def test_build_process_query_command_forces_utf8_output():
    command = build_process_query_command()

    assert command[:2] == ["powershell.exe", "-NoProfile"]
    assert "OutputEncoding" in command[-1]
    assert "UTF8" in command[-1]
