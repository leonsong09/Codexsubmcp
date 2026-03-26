from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "task_name": "CodexSubMcpWatchdog",
    "interval_minutes": 10,
    "max_suites": 6,
    "suite_window_seconds": 15,
    "codex_patterns": ["codex.exe", "@openai/codex/bin/codex.js"],
    "candidate_patterns": [
        "@modelcontextprotocol/",
        "agentation-mcp",
        "mcp-server-fetch",
        "ace-tool",
        "auggie",
        "--mcp",
    ],
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_positive_int(name: str, value: object) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_patterns(name: str, patterns: object) -> None:
    if not isinstance(patterns, list) or not patterns:
        raise ValueError(f"{name} must be a non-empty list")
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError(f"{name} contains an invalid pattern")


def validate_config(config: dict[str, object]) -> dict[str, object]:
    _validate_positive_int("interval_minutes", config.get("interval_minutes"))
    _validate_positive_int("max_suites", config.get("max_suites"))
    _validate_positive_int("suite_window_seconds", config.get("suite_window_seconds"))
    _validate_patterns("codex_patterns", config.get("codex_patterns"))
    _validate_patterns("candidate_patterns", config.get("candidate_patterns"))
    return config


def load_config(*, runtime_path: Path, example_path: Path | None = None) -> dict[str, object]:
    merged = dict(DEFAULT_CONFIG)
    if runtime_path.exists():
        merged.update(_read_json(runtime_path))
        return validate_config(merged)
    if example_path is not None and example_path.exists():
        merged.update(_read_json(example_path))
    return validate_config(merged)
