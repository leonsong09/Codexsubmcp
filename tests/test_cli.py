from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from codexsubmcp.cli import main
from codexsubmcp.core.config import DEFAULT_CONFIG
from codexsubmcp.core.models import ProcessInfo
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


def test_main_dry_run_headless_outputs_structured_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    config_path = tmp_path / "config.json"
    config = dict(DEFAULT_CONFIG)
    config["max_suites"] = 1
    config["candidate_patterns"] = ["agentation-mcp"]
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(
        "codexsubmcp.cli.load_windows_processes",
        lambda: [
            _proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server"),
            _proc(211, 210, "node.exe", "2026-03-24T09:00:01", "node agentation-mcp"),
            _proc(310, 9998, "node.exe", "2026-03-24T09:01:00", "agentation-mcp server"),
            _proc(311, 310, "node.exe", "2026-03-24T09:01:01", "node agentation-mcp"),
        ],
    )

    exit_code = main(["dry-run", "--headless", "--config", str(config_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["dry_run"] is True
    assert payload["cleanup_target_count"] == 1
    assert payload["actions"] == ["dry-run pid=210 processes=2"]


def test_main_cleanup_headless_writes_report_file(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config.json"
    report_path = tmp_path / "cleanup-report.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")

    monkeypatch.setattr(
        "codexsubmcp.cli.load_windows_processes",
        lambda: [_proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server")],
    )

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
