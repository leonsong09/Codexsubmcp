from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    ppid: int
    name: str
    created_at: datetime
    command_line: str


@dataclass(frozen=True)
class ProcessSuite:
    suite_id: str
    classification: str
    created_at: datetime
    root_pid: int
    processes: tuple[ProcessInfo, ...]
    live_codex_pid: int | None = None

    @property
    def process_ids(self) -> list[int]:
        return [process.pid for process in self.processes]


@dataclass(frozen=True)
class CleanupReport:
    suites: tuple[ProcessSuite, ...]
    cleanup_targets: tuple[ProcessSuite, ...]
    actions: list[str]


@dataclass(frozen=True)
class McpRecord:
    name: str
    category: str
    source: str
    command: str | None = None
    path: Path | None = None
    version: str | None = None
    confidence: str = "medium"
    notes: str | None = None
    type: str | None = None
    args: tuple[str, ...] = ()
    env_keys: tuple[str, ...] = ()
    startup_timeout_ms: int | None = None
    tool_timeout_sec: float | None = None
