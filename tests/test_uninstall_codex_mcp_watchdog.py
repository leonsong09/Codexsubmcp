from __future__ import annotations

from pathlib import Path

from tools.uninstall_codex_mcp_watchdog import build_unregister_task_script


def test_build_unregister_task_script_contains_task_name_and_unregister_command():
    script = build_unregister_task_script(task_name="CodexSubMcpWatchdog")

    assert "CodexSubMcpWatchdog" in script
    assert "Unregister-ScheduledTask" in script
    assert "-Confirm:$false" in script


def test_uninstall_powershell_wrapper_points_to_python_uninstaller(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    wrapper_path = project_root / "tools" / "uninstall_codex_mcp_watchdog.ps1"
    content = wrapper_path.read_text(encoding="utf-8")

    assert "uninstall_codex_mcp_watchdog.py" in content
    assert "venv\\Scripts\\python.exe" in content
