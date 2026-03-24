from __future__ import annotations

import json
from pathlib import Path

from tools.install_codex_mcp_watchdog import (
    build_register_task_script,
    ensure_runtime_config,
    resolve_project_python,
)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_resolve_project_python_prefers_venv_over_dot_venv(tmp_path):
    venv_python = tmp_path / "venv" / "Scripts" / "python.exe"
    dot_venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    _touch(venv_python)
    _touch(dot_venv_python)

    python_path = resolve_project_python(tmp_path)

    assert python_path == venv_python


def test_ensure_runtime_config_copies_example_once(tmp_path):
    example_path = tmp_path / "tools" / "codex_mcp_watchdog.example.json"
    runtime_path = tmp_path / "temp" / "codex_mcp_watchdog" / "config.json"
    example_path.parent.mkdir(parents=True, exist_ok=True)
    example_path.write_text(json.dumps({"max_suites": 6}), encoding="utf-8")

    created = ensure_runtime_config(example_path, runtime_path)

    assert created is True
    assert json.loads(runtime_path.read_text(encoding="utf-8")) == {"max_suites": 6}

    runtime_path.write_text(json.dumps({"max_suites": 9}), encoding="utf-8")
    created = ensure_runtime_config(example_path, runtime_path)

    assert created is False
    assert json.loads(runtime_path.read_text(encoding="utf-8")) == {"max_suites": 9}


def test_build_register_task_script_contains_runner_task_name_and_interval(tmp_path):
    runner_script = tmp_path / "tools" / "run_codex_mcp_watchdog.ps1"
    script = build_register_task_script(
        task_name="CodexSubMcpWatchdog",
        runner_script_path=runner_script,
        interval_minutes=10,
    )

    assert "CodexSubMcpWatchdog" in script
    assert str(runner_script) in script
    assert "Minutes 10" in script
    assert "Register-ScheduledTask" in script


def test_install_powershell_wrapper_points_to_python_installer(project_root: Path = Path(__file__).resolve().parents[1]):
    wrapper_path = project_root / "tools" / "install_codex_mcp_watchdog.ps1"
    content = wrapper_path.read_text(encoding="utf-8")

    assert "install_codex_mcp_watchdog.py" in content
    assert "venv\\Scripts\\python.exe" in content
