from __future__ import annotations

import json
import subprocess
from datetime import datetime

from codexsubmcp.core.models import ProcessInfo


def build_process_query_command() -> list[str]:
    query = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "Get-CimInstance Win32_Process | ForEach-Object { "
        "[PSCustomObject]@{ "
        "pid = [int]$_.ProcessId; "
        "ppid = [int]$_.ParentProcessId; "
        "name = [string]$_.Name; "
        "created_at = if ($_.CreationDate) { $_.CreationDate.ToString('o') } else { '' }; "
        "command_line = [string]$_.CommandLine } } | ConvertTo-Json -Compress"
    )
    return ["powershell.exe", "-NoProfile", "-Command", query]


def load_windows_processes() -> list[ProcessInfo]:
    result = subprocess.run(
        build_process_query_command(),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "无法读取 Windows 进程快照")
    payload = json.loads(result.stdout or "[]")
    rows = payload if isinstance(payload, list) else [payload]
    return [
        ProcessInfo(
            pid=int(row["pid"]),
            ppid=int(row["ppid"]),
            name=str(row.get("name") or ""),
            created_at=datetime.fromisoformat(row.get("created_at") or datetime.now().isoformat()),
            command_line=str(row.get("command_line") or ""),
        )
        for row in rows
    ]
