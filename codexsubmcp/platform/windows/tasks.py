from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TASK_NAME = "CodexSubMcpWatchdog"


@dataclass(frozen=True)
class TaskStatus:
    task_name: str
    installed: bool
    enabled: bool | None
    executable_path: Path | None
    arguments: str | None


def build_register_task_script(
    *,
    task_name: str,
    executable_path: Path,
    interval_minutes: int,
) -> str:
    escaped_executable = str(executable_path).replace("'", "''")
    escaped_task_name = task_name.replace("'", "''")
    escaped_arguments = "run-once --headless"
    return f"""
$taskName = '{escaped_task_name}'
$executable = '{escaped_executable}'
$arguments = '{escaped_arguments}'
$action = New-ScheduledTaskAction -Execute $executable -Argument $arguments
$repeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes {interval_minutes}) -RepetitionDuration (New-TimeSpan -Days 3650)
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logonTrigger, $repeatTrigger) -Description 'Codex subagent MCP watchdog' -Force | Out-Null
Write-Output "REGISTERED:$taskName"
""".strip()


def build_unregister_task_script(*, task_name: str) -> str:
    escaped_task_name = task_name.replace("'", "''")
    return f"""
$taskName = '{escaped_task_name}'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {{
    Write-Output "ABSENT:$taskName"
    exit 0
}}
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Output "UNREGISTERED:$taskName"
""".strip()


def build_get_task_status_script(*, task_name: str) -> str:
    escaped_task_name = task_name.replace("'", "''")
    return f"""
$taskName = '{escaped_task_name}'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {{
    Write-Output ""
    exit 0
}}
$action = $task.Actions | Select-Object -First 1
[PSCustomObject]@{{
    TaskName = $task.TaskName
    State = [string]$task.State
    Execute = [string]$action.Execute
    Arguments = [string]$action.Arguments
}} | ConvertTo-Json -Compress
""".strip()


def build_set_task_enabled_script(*, task_name: str, enabled: bool) -> str:
    escaped_task_name = task_name.replace("'", "''")
    command = "Enable-ScheduledTask" if enabled else "Disable-ScheduledTask"
    return f"""
$taskName = '{escaped_task_name}'
{command} -TaskName $taskName | Out-Null
Write-Output "{'ENABLED' if enabled else 'DISABLED'}:$taskName"
""".strip()


def parse_task_status(payload: dict[str, Any] | None) -> TaskStatus:
    if not payload:
        return TaskStatus(
            task_name=DEFAULT_TASK_NAME,
            installed=False,
            enabled=None,
            executable_path=None,
            arguments=None,
        )
    state = str(payload.get("State") or "")
    return TaskStatus(
        task_name=str(payload.get("TaskName") or DEFAULT_TASK_NAME),
        installed=True,
        enabled=state.lower() != "disabled",
        executable_path=Path(str(payload["Execute"])) if payload.get("Execute") else None,
        arguments=str(payload.get("Arguments") or "") or None,
    )


def _run_powershell(script: str) -> str:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "PowerShell command failed")
    return result.stdout.strip()


def register_task(*, task_name: str, executable_path: Path, interval_minutes: int) -> str:
    return _run_powershell(
        build_register_task_script(
            task_name=task_name,
            executable_path=executable_path,
            interval_minutes=interval_minutes,
        )
    )


def unregister_task(*, task_name: str) -> str:
    return _run_powershell(build_unregister_task_script(task_name=task_name))


def get_task_status(*, task_name: str) -> TaskStatus:
    output = _run_powershell(build_get_task_status_script(task_name=task_name))
    payload = json.loads(output) if output else None
    return parse_task_status(payload)


def set_task_enabled(*, task_name: str, enabled: bool) -> str:
    return _run_powershell(build_set_task_enabled_script(task_name=task_name, enabled=enabled))
