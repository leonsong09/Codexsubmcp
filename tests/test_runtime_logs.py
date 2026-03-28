from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from codexsubmcp.core.analysis import analyze_snapshot
from codexsubmcp.core.cleanup import build_cleanup_preview, execute_cleanup_preview
from codexsubmcp.core.models import McpRecord, ProcessInfo
from codexsubmcp.core.runtime_logs import (
    load_lifetime_stats,
    write_cleanup_log,
    write_preview_log,
    write_refresh_log,
)
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


def _snapshot_bundle():
    snapshot = SystemSnapshot(
        snapshot_id="snapshot-logs",
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
    analysis = analyze_snapshot(snapshot)
    preview = build_cleanup_preview(analysis)
    cleanup_result = execute_cleanup_preview(preview, kill_runner=lambda _pid: None)
    return snapshot, analysis, preview, cleanup_result


def test_runtime_log_writers_create_refresh_preview_and_cleanup_files(tmp_path):
    snapshot, analysis, preview, cleanup_result = _snapshot_bundle()

    refresh_path = write_refresh_log(snapshot=snapshot, analysis=analysis, log_dir=tmp_path)
    preview_path = write_preview_log(preview=preview, log_dir=tmp_path)
    cleanup_path = write_cleanup_log(result=cleanup_result, log_dir=tmp_path)

    assert refresh_path.name.startswith("refresh-")
    assert preview_path.name.startswith("preview-")
    assert cleanup_path.name.startswith("cleanup-")
    assert "\"kind\": \"refresh\"" in refresh_path.read_text(encoding="utf-8")
    assert "\"kind\": \"preview\"" in preview_path.read_text(encoding="utf-8")
    assert "\"kind\": \"cleanup\"" in cleanup_path.read_text(encoding="utf-8")


def test_lifetime_stats_only_count_successful_cleanup_logs(tmp_path):
    _snapshot, _analysis, _preview, cleanup_result = _snapshot_bundle()
    failed_result = replace(
        cleanup_result,
        executed_at=datetime.fromisoformat("2026-03-28T12:05:00"),
        summary=replace(
            cleanup_result.summary,
            success=False,
            failed_target_count=1,
            closed_suite_count=0,
            closed_stale_branch_count=0,
            killed_mcp_instance_count=0,
            killed_process_count=0,
        ),
    )
    success_result = replace(cleanup_result, executed_at=datetime.fromisoformat("2026-03-28T12:04:00"))

    write_cleanup_log(result=failed_result, log_dir=tmp_path)
    write_cleanup_log(result=success_result, log_dir=tmp_path)
    stats = load_lifetime_stats(log_dir=tmp_path)

    assert stats.total_cleanup_count == 1
    assert stats.total_closed_suite_count == 1
    assert stats.total_closed_stale_branch_count == 1


def test_refresh_and_preview_logs_do_not_pollute_cleanup_totals(tmp_path):
    snapshot, analysis, preview, cleanup_result = _snapshot_bundle()

    write_refresh_log(snapshot=snapshot, analysis=analysis, log_dir=tmp_path)
    write_preview_log(preview=preview, log_dir=tmp_path)
    write_cleanup_log(result=cleanup_result, log_dir=tmp_path)
    stats = load_lifetime_stats(log_dir=tmp_path)

    assert stats.total_refresh_count == 1
    assert stats.total_preview_count == 1
    assert stats.total_closed_suite_count == 1
    assert stats.total_closed_stale_branch_count == 1
    assert stats.total_killed_mcp_instance_count == 2
    assert stats.total_killed_process_count == 4


def test_lifetime_stats_use_latest_successful_cleanup_timestamp(tmp_path):
    _snapshot, _analysis, _preview, cleanup_result = _snapshot_bundle()
    older = replace(cleanup_result, executed_at=datetime.fromisoformat("2026-03-28T12:03:00"))
    failed = replace(
        cleanup_result,
        executed_at=datetime.fromisoformat("2026-03-28T12:06:00"),
        summary=replace(cleanup_result.summary, success=False, failed_target_count=1),
    )
    latest_success = replace(cleanup_result, executed_at=datetime.fromisoformat("2026-03-28T12:07:00"))

    write_cleanup_log(result=older, log_dir=tmp_path)
    write_cleanup_log(result=failed, log_dir=tmp_path)
    write_cleanup_log(result=latest_success, log_dir=tmp_path)
    stats = load_lifetime_stats(log_dir=tmp_path)

    assert stats.last_cleanup_at == datetime.fromisoformat("2026-03-28T12:07:00")
