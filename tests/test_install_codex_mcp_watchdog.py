from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tools.install_codex_mcp_watchdog import (
    build_register_task_script,
    ensure_runtime_config,
    resolve_project_python,
)
from tools.setup_codex_mcp_watchdog import run_setup


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
    assert "Register-ScheduledTask" in script


def test_install_powershell_wrapper_points_to_python_installer(project_root: Path = Path(__file__).resolve().parents[1]):
    wrapper_path = project_root / "tools" / "install_codex_mcp_watchdog.ps1"
    content = wrapper_path.read_text(encoding="utf-8")

    assert "install_codex_mcp_watchdog.py" in content
    assert "venv\\Scripts\\python.exe" in content


def test_run_setup_bootstraps_venv_then_installs_dry_runs_and_registers(tmp_path):
    bootstrap_python = tmp_path / "python.exe"
    cleanup_script = tmp_path / "tools" / "cleanup_codex_mcp_orphans.py"
    install_script = tmp_path / "tools" / "install_codex_mcp_watchdog.py"
    _touch(bootstrap_python)
    _touch(cleanup_script)
    _touch(install_script)
    commands: list[tuple[list[str], Path, bool]] = []

    def fake_runner(command, *, cwd, check):
        commands.append((command, cwd, check))

        class Result:
            returncode = 0

        return Result()

    exit_code = run_setup(
        project_root=tmp_path,
        bootstrap_python=bootstrap_python,
        runner=fake_runner,
    )

    venv_python = tmp_path / "venv" / "Scripts" / "python.exe"
    assert exit_code == 0
    assert commands == [
        ([str(bootstrap_python), "-m", "venv", str(tmp_path / "venv")], tmp_path, False),
        ([str(venv_python), "-m", "pip", "install", "-e", ".[dev]"], tmp_path, False),
        ([str(venv_python), str(cleanup_script)], tmp_path, False),
        ([str(venv_python), str(install_script)], tmp_path, False),
    ]


def test_run_setup_reuses_existing_venv_without_recreating_it(tmp_path):
    bootstrap_python = tmp_path / "python.exe"
    venv_python = tmp_path / "venv" / "Scripts" / "python.exe"
    cleanup_script = tmp_path / "tools" / "cleanup_codex_mcp_orphans.py"
    install_script = tmp_path / "tools" / "install_codex_mcp_watchdog.py"
    _touch(bootstrap_python)
    _touch(venv_python)
    _touch(cleanup_script)
    _touch(install_script)
    commands: list[list[str]] = []

    def fake_runner(command, *, cwd, check):
        commands.append(command)

        class Result:
            returncode = 0

        return Result()

    exit_code = run_setup(
        project_root=tmp_path,
        bootstrap_python=bootstrap_python,
        runner=fake_runner,
    )

    assert exit_code == 0
    assert commands == [
        [str(venv_python), "-m", "pip", "install", "-e", ".[dev]"],
        [str(venv_python), str(cleanup_script)],
        [str(venv_python), str(install_script)],
    ]


def test_setup_powershell_wrapper_prefers_venv_and_falls_back_to_system_python(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    wrapper_path = project_root / "tools" / "setup_codex_mcp_watchdog.ps1"
    content = wrapper_path.read_text(encoding="utf-8")

    assert "setup_codex_mcp_watchdog.py" in content
    assert "venv\\Scripts\\python.exe" in content
    assert "Get-Command python.exe" in content


def test_setup_python_entrypoint_runs_as_script(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, str(project_root / "tools" / "setup_codex_mcp_watchdog.py"), "--help"],
        cwd=project_root,
        capture_output=True,
        check=False,
        env=env,
    )
    stdout = result.stdout.decode("utf-8")

    assert result.returncode == 0
    assert "一键初始化 Codex MCP watchdog" in stdout
