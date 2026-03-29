from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from codexsubmcp.cli import main
from codexsubmcp.core.analysis import AnalysisResult, AnalysisSummary
from codexsubmcp.core.cleanup_workflow import (
    CleanupPreview,
    CleanupPreviewSummary,
    CleanupResult,
    CleanupResultSummary,
)
from codexsubmcp.core.config import DEFAULT_CONFIG
from codexsubmcp.core.models import McpRecord, ProcessInfo
from codexsubmcp.core.recognition import RecognitionReport
from codexsubmcp.core.system_snapshot import CodexRuntimeSnapshot, SystemSnapshot
from codexsubmcp.platform.windows.tasks import TaskStatus


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


def _snapshot() -> SystemSnapshot:
    return SystemSnapshot(
        snapshot_id="snapshot-cli",
        captured_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        codex=CodexRuntimeSnapshot(
            global_config_path=Path("C:/Users/test/.codex/config.toml"),
            project_config_path=None,
            state_db_path=Path("C:/Users/test/.codex/state_5.sqlite"),
            open_subagent_count=2,
        ),
        configured_mcps=(
            McpRecord(name="memory", category="configured", source="codex_global_config", command="npx"),
        ),
        processes=(),
    )


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        snapshot_id="snapshot-cli",
        analyzed_at=datetime.fromisoformat("2026-03-28T12:01:00"),
        summary=AnalysisSummary(
            configured_mcp_count=1,
            running_mcp_instance_count=2,
            open_subagent_count=2,
            drift_missing_runtime_count=0,
            drift_unconfigured_runtime_count=1,
            live_suite_count=1,
            orphan_suite_count=1,
        ),
        running_mcps=(),
        configured_not_running=(),
        running_not_configured=("agentation-mcp",),
        live_suites=(),
        orphan_suites=(),
    )


def _preview() -> CleanupPreview:
    return CleanupPreview(
        snapshot_id="snapshot-cli",
        previewed_at=datetime.fromisoformat("2026-03-28T12:02:00"),
        summary=CleanupPreviewSummary(target_count=1),
        targets=(),
    )


def _cleanup_result() -> CleanupResult:
    return CleanupResult(
        snapshot_id="snapshot-cli",
        executed_at=datetime.fromisoformat("2026-03-28T12:03:00"),
        summary=CleanupResultSummary(
            success=True,
            target_count=1,
            failed_target_count=0,
            closed_suite_count=1,
            killed_mcp_instance_count=1,
            killed_process_count=2,
        ),
        target_results=(),
    )


def _recognition(status: str = "trusted", reason: str = "ok") -> RecognitionReport:
    return RecognitionReport(
        status=status,
        reason=reason,
        live_sample_count=1,
        matched_codex_process_count=2,
        verified_live_parent_count=1,
        unmatched_live_parent_count=0 if status == "trusted" else 1,
    )


def test_module_help_lists_subcommands(project_root: Path = Path(__file__).resolve().parents[1]):
    result = subprocess.run(
        [sys.executable, "-m", "codexsubmcp", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "gui" in result.stdout
    assert "refresh" in result.stdout
    assert "preview" in result.stdout
    assert "run-once" in result.stdout
    assert "dry-run" in result.stdout
    assert "cleanup" in result.stdout
    assert "task" in result.stdout
    assert "scan" in result.stdout
    assert "config" in result.stdout


def test_main_without_args_launches_gui(monkeypatch, capsys):
    seen: list[str] = []

    monkeypatch.setattr("codexsubmcp.cli.launch_gui", lambda: seen.append("gui") or 0)

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert seen == ["gui"]
    assert captured.out == ""


def test_main_refresh_headless_outputs_new_summary_fields(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("codexsubmcp.cli.build_system_snapshot", lambda **_kwargs: _snapshot())
    monkeypatch.setattr("codexsubmcp.cli.analyze_snapshot", lambda *_args, **_kwargs: _analysis())
    monkeypatch.setattr("codexsubmcp.cli.validate_parent_recognition", lambda *_args, **_kwargs: _recognition())

    exit_code = main(["refresh", "--headless"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["kind"] == "refresh"
    assert payload["summary"]["configured_mcp_count"] == 1
    assert payload["summary"]["running_mcp_instance_count"] == 2
    assert payload["recognition"]["status"] == "trusted"


def test_main_preview_headless_outputs_new_summary_fields(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("codexsubmcp.cli.build_system_snapshot", lambda **_kwargs: _snapshot())
    monkeypatch.setattr("codexsubmcp.cli.analyze_snapshot", lambda *_args, **_kwargs: _analysis())
    monkeypatch.setattr("codexsubmcp.cli.validate_parent_recognition", lambda *_args, **_kwargs: _recognition())
    monkeypatch.setattr("codexsubmcp.cli.build_cleanup_preview", lambda *_args, **_kwargs: _preview())

    exit_code = main(["preview", "--headless"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["kind"] == "preview"
    assert payload["summary"]["target_count"] == 1


def test_main_cleanup_headless_writes_report_file(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config.json"
    report_path = tmp_path / "cleanup-report.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    monkeypatch.setattr("codexsubmcp.cli.build_system_snapshot", lambda **_kwargs: _snapshot())
    monkeypatch.setattr("codexsubmcp.cli.analyze_snapshot", lambda *_args, **_kwargs: _analysis())
    monkeypatch.setattr("codexsubmcp.cli.validate_parent_recognition", lambda *_args, **_kwargs: _recognition())
    monkeypatch.setattr("codexsubmcp.cli.build_cleanup_preview", lambda *_args, **_kwargs: _preview())
    monkeypatch.setattr("codexsubmcp.cli.execute_cleanup_preview", lambda *_args, **_kwargs: _cleanup_result())

    exit_code = main(
        [
            "cleanup",
            "--yes",
            "--headless",
            "--config",
            str(config_path),
            "--report-file",
            str(report_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    assert payload["kind"] == "cleanup"
    assert payload["summary"]["success"] is True
    assert payload["summary"]["closed_suite_count"] == 1
    assert Path(payload["log_path"]).exists()


def test_run_once_executes_orphan_cleanup_when_recognition_is_trusted(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("codexsubmcp.cli.build_system_snapshot", lambda **_kwargs: _snapshot())
    monkeypatch.setattr("codexsubmcp.cli.analyze_snapshot", lambda *_args, **_kwargs: _analysis())
    monkeypatch.setattr("codexsubmcp.cli.validate_parent_recognition", lambda *_args, **_kwargs: _recognition())
    monkeypatch.setattr("codexsubmcp.cli.build_cleanup_preview", lambda *_args, **_kwargs: _preview())

    seen: dict[str, object] = {}

    def fake_execute(preview, *, kill_runner):
        seen["preview"] = preview
        return CleanupResult(
            snapshot_id="snapshot-cli",
            executed_at=datetime.fromisoformat("2026-03-28T12:03:00"),
            summary=CleanupResultSummary(
                success=True,
                target_count=1,
                failed_target_count=0,
                closed_suite_count=1,
                killed_mcp_instance_count=1,
                killed_process_count=2,
            ),
            target_results=(),
        )

    monkeypatch.setattr("codexsubmcp.cli.execute_cleanup_preview", fake_execute)

    exit_code = main(["run-once", "--headless", "--config", str(config_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["preview"] == _preview()
    assert payload["summary"]["closed_suite_count"] == 1


def test_main_preview_blocks_when_recognition_is_not_trusted(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("codexsubmcp.cli.build_system_snapshot", lambda **_kwargs: _snapshot())
    monkeypatch.setattr("codexsubmcp.cli.analyze_snapshot", lambda *_args, **_kwargs: _analysis())
    monkeypatch.setattr(
        "codexsubmcp.cli.validate_parent_recognition",
        lambda *_args, **_kwargs: _recognition(status="blocked", reason="blocked"),
    )

    try:
        main(["preview", "--headless"])
    except RuntimeError as exc:
        assert str(exc) == "blocked"
    else:
        raise AssertionError("preview should block when recognition is not trusted")


def test_main_config_validate_returns_zero_for_valid_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")

    assert main(["config", "validate", "--config", str(config_path)]) == 0


def test_main_task_status_outputs_structured_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "codexsubmcp.cli.get_task_status",
        lambda task_name: TaskStatus(
            task_name=task_name,
            installed=True,
            enabled=True,
            executable_path=Path("C:/Tools/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
        ),
    )

    exit_code = main(["task", "status", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["task_name"] == "CodexSubMcpWatchdog"
    assert payload["installed"] is True
    assert payload["enabled"] is True
    assert payload["arguments"] == "run-once --headless"


def test_main_task_install_calls_register_task(monkeypatch, tmp_path):
    executable_path = tmp_path / "CodexSubMcpManager.exe"
    executable_path.write_text("exe", encoding="utf-8")
    stable_path = tmp_path / "stable" / "CodexSubMcpManager.exe"
    seen: list[tuple[str, Path, int]] = []

    monkeypatch.setattr(
        "codexsubmcp.cli.install_current_executable",
        lambda path: stable_path,
    )
    monkeypatch.setattr(
        "codexsubmcp.cli.register_task",
        lambda task_name, executable_path, interval_minutes: seen.append(
            (task_name, executable_path, interval_minutes)
        )
        or "REGISTERED:CodexSubMcpWatchdog",
    )

    exit_code = main(
        [
            "task",
            "install",
            "--executable-path",
            str(executable_path),
            "--interval",
            "5",
        ]
    )

    assert exit_code == 0
    assert seen == [("CodexSubMcpWatchdog", stable_path, 5)]
