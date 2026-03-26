from __future__ import annotations

import json
from pathlib import Path

from codexsubmcp.app_paths import (
    APP_DIR_NAME,
    build_runtime_paths,
    ensure_runtime_config,
    find_legacy_config,
)


def test_build_runtime_paths_uses_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    paths = build_runtime_paths()

    assert paths.root == tmp_path / APP_DIR_NAME
    assert paths.config == tmp_path / APP_DIR_NAME / "config.json"
    assert paths.logs == tmp_path / APP_DIR_NAME / "logs"
    assert paths.cache == tmp_path / APP_DIR_NAME / "cache"
    assert paths.exports == tmp_path / APP_DIR_NAME / "exports"
    assert paths.bin_dir == tmp_path / APP_DIR_NAME / "bin"


def test_ensure_runtime_config_creates_default_json(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    config_path = ensure_runtime_config()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["task_name"] == "CodexSubMcpWatchdog"
    assert payload["max_suites"] == 6
    assert payload["candidate_patterns"][-1] == "--mcp"


def test_find_legacy_config_returns_temp_runtime_config(tmp_path):
    project_root = tmp_path / "project"
    legacy_config = project_root / "temp" / "codex_mcp_watchdog" / "config.json"
    legacy_config.parent.mkdir(parents=True, exist_ok=True)
    legacy_config.write_text("{}", encoding="utf-8")

    assert find_legacy_config(project_root) == legacy_config
