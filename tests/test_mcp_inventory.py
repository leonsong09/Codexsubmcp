from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from codexsubmcp.cli import main
from codexsubmcp.core.analysis import AnalysisResult, AnalysisSummary, RunningMcpSummary
from codexsubmcp.core.mcp_inventory import build_inventory
from codexsubmcp.core.models import McpRecord
from codexsubmcp.core.system_snapshot import CodexRuntimeSnapshot, SystemSnapshot


def _snapshot() -> SystemSnapshot:
    return SystemSnapshot(
        snapshot_id="snapshot-mcp",
        captured_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        codex=CodexRuntimeSnapshot(
            global_config_path=Path("C:/Users/test/.codex/config.toml"),
            project_config_path=None,
            state_db_path=Path("C:/Users/test/.codex/state_5.sqlite"),
            open_subagent_count=2,
        ),
        configured_mcps=(
            McpRecord(
                name="memory",
                category="configured",
                source="codex_global_config",
                command="npx",
                args=("-y", "@modelcontextprotocol/server-memory"),
                type="stdio",
            ),
        ),
        processes=(),
    )


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        snapshot_id="snapshot-mcp",
        analyzed_at=datetime.fromisoformat("2026-03-28T12:01:00"),
        summary=AnalysisSummary(
            configured_mcp_count=1,
            running_mcp_instance_count=2,
            open_subagent_count=2,
            drift_missing_runtime_count=0,
            drift_unconfigured_runtime_count=1,
            live_suite_count=1,
            orphan_suite_count=0,
        ),
        running_mcps=(
            RunningMcpSummary(
                tool_signature="agentation-mcp",
                instance_count=2,
                live_codex_pid_count=1,
            ),
        ),
        configured_not_running=(),
        running_not_configured=("agentation-mcp",),
        live_suites=(),
        orphan_suites=(),
    )


def test_build_inventory_returns_configured_running_and_drift_sections():
    payload = build_inventory(
        configured=list(_snapshot().configured_mcps),
        running=list(_analysis().running_mcps),
        drift={
            "configured_not_running": [],
            "running_not_configured": ["agentation-mcp"],
        },
    )

    assert list(payload) == ["configured", "running", "drift"]
    assert payload["configured"][0]["name"] == "memory"
    assert payload["running"][0]["tool_signature"] == "agentation-mcp"
    assert payload["drift"]["running_not_configured"] == ["agentation-mcp"]


def test_scan_mcp_cli_returns_grouped_json_without_installed_candidates(monkeypatch, capsys):
    monkeypatch.setattr("codexsubmcp.cli.build_system_snapshot", lambda **_kwargs: _snapshot())
    monkeypatch.setattr("codexsubmcp.cli.analyze_snapshot", lambda *_args, **_kwargs: _analysis())

    exit_code = main(["scan", "mcp", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert list(payload) == ["configured", "running", "drift"]
    assert payload["configured"][0]["name"] == "memory"
    assert payload["running"][0]["tool_signature"] == "agentation-mcp"
    assert payload["drift"]["running_not_configured"] == ["agentation-mcp"]
    assert "installed_candidates" not in payload
