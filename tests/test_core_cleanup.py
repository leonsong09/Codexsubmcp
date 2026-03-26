from __future__ import annotations

from datetime import datetime

from codexsubmcp.core.cleanup import build_candidate_suites, run_cleanup
from codexsubmcp.core.models import ProcessInfo, ProcessSuite


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


def test_build_candidate_suites_returns_process_suite_models():
    processes = [
        _proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server"),
        _proc(211, 210, "node.exe", "2026-03-24T09:00:01", "node agentation-mcp"),
    ]

    suites = build_candidate_suites(processes, suite_window_seconds=15)

    assert len(suites) == 1
    assert isinstance(suites[0], ProcessSuite)
    assert suites[0].process_ids == [210, 211]


def test_run_cleanup_returns_structured_report_for_dry_run():
    processes = [
        _proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server"),
        _proc(211, 210, "node.exe", "2026-03-24T09:00:01", "node agentation-mcp"),
        _proc(310, 9998, "node.exe", "2026-03-24T09:01:00", "agentation-mcp server"),
        _proc(311, 310, "node.exe", "2026-03-24T09:01:01", "node agentation-mcp"),
    ]
    seen: list[int] = []

    report = run_cleanup(
        processes,
        config={
            "max_suites": 1,
            "suite_window_seconds": 15,
            "codex_patterns": ["codex.exe"],
            "candidate_patterns": ["agentation-mcp"],
        },
        dry_run=True,
        kill_runner=lambda pid: seen.append(pid),
    )

    assert len(report.suites) == 2
    assert len(report.cleanup_targets) == 1
    assert report.actions == ["dry-run pid=210 processes=2"]
    assert seen == []
