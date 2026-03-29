from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from codexsubmcp.core.analysis import analyze_snapshot
from codexsubmcp.core.cleanup import build_cleanup_preview, execute_cleanup_preview
from codexsubmcp.core.models import McpRecord, ProcessInfo
from codexsubmcp.core.system_snapshot import CodexRuntimeSnapshot, SystemSnapshot


def _proc(pid: int, ppid: int, created_at: str, command_line: str) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        name="node.exe",
        created_at=datetime.fromisoformat(created_at),
        command_line=command_line,
    )


def _configured_record(name: str, *args: str) -> McpRecord:
    return McpRecord(
        name=name,
        category="configured",
        source="codex_global_config",
        command="npx",
        args=args,
        type="stdio",
    )


def _preview():
    snapshot = SystemSnapshot(
        snapshot_id="snapshot-cleanup",
        captured_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        codex=CodexRuntimeSnapshot(
            global_config_path=Path("C:/Users/test/.codex/config.toml"),
            project_config_path=None,
            state_db_path=Path("C:/Users/test/.codex/state_5.sqlite"),
            open_subagent_count=2,
        ),
        configured_mcps=(
            _configured_record("agentation", "-y", "agentation-mcp", "server"),
            _configured_record("memory", "-y", "@modelcontextprotocol/server-memory"),
        ),
        processes=(
            _proc(100, 1, "2026-03-28T11:59:00", "codex.exe"),
            _proc(110, 100, "2026-03-28T12:00:00", "cmd /c npx -y agentation-mcp server"),
            _proc(111, 110, "2026-03-28T12:00:01", "node agentation-mcp cli.js server"),
            _proc(120, 100, "2026-03-28T12:01:00", "cmd /c npx -y agentation-mcp server"),
            _proc(121, 120, "2026-03-28T12:01:01", "node agentation-mcp cli.js server"),
            _proc(210, 9999, "2026-03-28T12:02:00", "cmd /c npx -y @modelcontextprotocol/server-memory"),
            _proc(211, 210, "2026-03-28T12:02:01", "node npx-cli.js @modelcontextprotocol/server-memory"),
        ),
    )
    return build_cleanup_preview(analyze_snapshot(snapshot))


def test_execute_cleanup_preview_kills_orphan_suite_root_and_records_action():
    preview = _preview()
    orphan_target = next(target for target in preview.targets if target.target_type == "orphan_suite")
    preview = replace(preview, targets=(orphan_target,))
    seen: list[int] = []

    result = execute_cleanup_preview(preview, kill_runner=lambda pid: seen.append(pid))

    assert seen == [210]
    assert result.target_results[0].target_type == "orphan_suite"
    assert result.target_results[0].status == "killed"
    assert result.target_results[0].killed_process_ids == (210, 211)

def test_execute_cleanup_preview_summarizes_closed_targets_and_processes():
    seen: list[int] = []

    result = execute_cleanup_preview(
        _preview(),
        kill_runner=lambda pid: seen.append(pid),
    )

    assert seen == [210]
    assert result.summary.closed_suite_count == 1
    assert result.summary.killed_mcp_instance_count == 1
    assert result.summary.killed_process_count == 2


def test_execute_cleanup_preview_keeps_other_successes_when_one_target_fails():
    def fake_kill(pid: int) -> None:
        raise RuntimeError("taskkill failed")

    result = execute_cleanup_preview(
        _preview(),
        kill_runner=fake_kill,
    )

    assert result.summary.failed_target_count == 1
    assert result.summary.closed_suite_count == 0
    assert [item.status for item in result.target_results] == ["failed"]
