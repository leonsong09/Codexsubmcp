from __future__ import annotations

from pathlib import Path

from codexsubmcp.platform.windows.elevation import build_runas_invocation
from codexsubmcp.platform.windows.install_artifact import (
    STABLE_EXE_NAME,
    install_current_executable,
)
from codexsubmcp.platform.windows.tasks import (
    TaskStatus,
    build_register_task_script,
    parse_task_status,
)


def test_build_register_task_script_targets_stable_executable(tmp_path):
    executable_path = tmp_path / "CodexSubMcpManager.exe"
    script = build_register_task_script(
        task_name="CodexSubMcpWatchdog",
        executable_path=executable_path,
        interval_minutes=10,
    )

    assert "CodexSubMcpWatchdog" in script
    assert str(executable_path) in script
    assert "run-once --headless" in script
    assert "Minutes 10" in script


def test_install_current_executable_overwrites_stable_target(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    source_path = tmp_path / "Downloads" / "manager.exe"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("v1", encoding="utf-8")

    installed_path = install_current_executable(source_path)
    source_path.write_text("v2", encoding="utf-8")
    overwritten_path = install_current_executable(source_path)

    assert installed_path.name == STABLE_EXE_NAME
    assert overwritten_path == installed_path
    assert overwritten_path.read_text(encoding="utf-8") == "v2"


def test_build_runas_invocation_includes_target_subcommand():
    invocation = build_runas_invocation(
        executable_path=Path("C:/Tools/CodexSubMcpManager.exe"),
        arguments=["task", "install", "--interval", "10"],
    )

    assert invocation.verb == "runas"
    assert invocation.executable_path == Path("C:/Tools/CodexSubMcpManager.exe")
    assert "task install --interval 10" in invocation.parameters


def test_parse_task_status_handles_disabled_task():
    status = parse_task_status(
        {
            "TaskName": "CodexSubMcpWatchdog",
            "State": "Disabled",
            "Execute": "C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe",
            "Arguments": "run-once --headless",
        }
    )

    assert status == TaskStatus(
        task_name="CodexSubMcpWatchdog",
        installed=True,
        enabled=False,
        executable_path=Path("C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe"),
        arguments="run-once --headless",
    )


def test_parse_task_status_parses_interval_and_next_run_time():
    status = parse_task_status(
        {
            "TaskName": "CodexSubMcpWatchdog",
            "State": "Ready",
            "Execute": "C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe",
            "Arguments": "run-once --headless",
            "RepetitionInterval": "PT15M",
            "NextRunTime": "2026-03-26T10:30:00",
        }
    )

    assert status == TaskStatus(
        task_name="CodexSubMcpWatchdog",
        installed=True,
        enabled=True,
        executable_path=Path("C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe"),
        arguments="run-once --headless",
        interval_minutes=15,
        next_run_time="2026-03-26T10:30:00",
    )
