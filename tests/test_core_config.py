from __future__ import annotations

import json

import pytest

from codexsubmcp.core.config import load_config, validate_config


def test_load_config_prefers_runtime_file_over_example(tmp_path):
    runtime_path = tmp_path / "runtime.json"
    example_path = tmp_path / "example.json"
    runtime_path.write_text(json.dumps({"max_suites": 9}), encoding="utf-8")
    example_path.write_text(json.dumps({"max_suites": 6}), encoding="utf-8")

    config = load_config(runtime_path=runtime_path, example_path=example_path)

    assert config["max_suites"] == 9


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_suites", 0),
        ("interval_minutes", 0),
        ("candidate_patterns", ["", "agentation-mcp"]),
    ],
)
def test_validate_config_rejects_invalid_values(field, value):
    config = {
        "task_name": "CodexSubMcpWatchdog",
        "interval_minutes": 10,
        "max_suites": 6,
        "suite_window_seconds": 15,
        "codex_patterns": ["codex.exe"],
        "candidate_patterns": ["agentation-mcp"],
    }
    config[field] = value

    with pytest.raises(ValueError):
        validate_config(config)
