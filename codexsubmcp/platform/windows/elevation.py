from __future__ import annotations

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
