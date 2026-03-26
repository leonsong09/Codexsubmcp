from __future__ import annotations

import ctypes
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class RunasInvocation:
    verb: str
    executable_path: Path
    parameters: str


def build_runas_invocation(*, executable_path: Path, arguments: Sequence[str]) -> RunasInvocation:
    return RunasInvocation(
        verb="runas",
        executable_path=executable_path,
        parameters=subprocess.list2cmdline(list(arguments)),
    )


def is_user_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def run_elevated(executable_path: Path, arguments: Sequence[str]) -> int:
    invocation = build_runas_invocation(executable_path=executable_path, arguments=arguments)
    escaped_file_path = str(invocation.executable_path).replace("'", "''")
    escaped_parameters = invocation.parameters.replace("'", "''")
    command = (
        "$process = Start-Process "
        f"-FilePath '{escaped_file_path}' "
        f"-ArgumentList '{escaped_parameters}' "
        "-Verb RunAs -Wait -PassThru; "
        "exit $process.ExitCode"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Elevated command failed")
    return result.returncode
