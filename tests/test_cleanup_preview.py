from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from codexsubmcp.core.analysis import analyze_snapshot
from codexsubmcp.core.cleanup import build_cleanup_preview
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


def _analysis_result():
    snapshot = SystemSnapshot(
        snapshot_id="snapshot-preview",
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
    return analyze_snapshot(snapshot)


def test_build_cleanup_preview_unifies_orphan_and_stale_targets():
    preview = build_cleanup_preview(_analysis_result())

    assert [target.target_type for target in preview.targets] == ["orphan_suite"]
    assert preview.targets[0].suite_id == "orphan-1"


def test_build_cleanup_preview_counts_targets_by_type():
    preview = build_cleanup_preview(_analysis_result())

    assert preview.summary.target_count == 1


def test_build_cleanup_preview_targets_include_reason_risk_and_process_ids():
    preview = build_cleanup_preview(_analysis_result())

    orphan_target = preview.targets[0]

    assert orphan_target.reason
    assert "Codex" in orphan_target.reason
    assert orphan_target.process_ids == (210, 211)


def test_build_cleanup_preview_requires_analysis_result():
    with pytest.raises(ValueError):
        build_cleanup_preview(None)
