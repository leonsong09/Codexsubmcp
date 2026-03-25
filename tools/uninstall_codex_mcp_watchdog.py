from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Sequence


DEFAULT_TASK_NAME = "CodexSubMcpWatchdog"


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="卸载 Codex MCP watchdog 计划任务")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    args = parser.parse_args(argv)

    script = build_unregister_task_script(task_name=args.task_name)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip() or "[ERROR] failed to unregister task", file=sys.stderr)
        return result.returncode or 1

    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
