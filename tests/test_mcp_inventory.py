from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codexsubmcp.cli import main
from codexsubmcp.platform.windows.mcp_sources import (
    scan_configured_sources,
    scan_npm_global_packages,
)


def test_scan_configured_sources_returns_configured_records(tmp_path):
    config_path = tmp_path / "codex_mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "memory": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-memory"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    records = scan_configured_sources([config_path])

    assert len(records) == 1
    assert records[0].category == "configured"
    assert records[0].source == "codex_config"
    assert records[0].name == "memory"


def test_scan_npm_global_packages_returns_installed_candidates(monkeypatch):
    def fake_run(*_args, **_kwargs):
        class Result:
            returncode = 0
            stdout = json.dumps(
                {
                    "dependencies": {
                        "@modelcontextprotocol/server-filesystem": {"version": "1.0.0"},
                        "left-pad": {"version": "1.3.0"},
                    }
                }
            )
            stderr = ""

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    records = scan_npm_global_packages()

    assert len(records) == 1
    assert records[0].category == "installed_candidate"
    assert records[0].source == "npm_global"
    assert records[0].name == "@modelcontextprotocol/server-filesystem"


def test_scan_mcp_cli_returns_grouped_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "codexsubmcp.cli.scan_configured_sources",
        lambda: [
            type(
                "Record",
                (),
                {
                    "name": "memory",
                    "category": "configured",
                    "source": "codex_config",
                    "command": "npx",
                    "path": None,
                    "version": None,
                    "confidence": "high",
                    "notes": None,
                },
            )()
        ],
    )
    monkeypatch.setattr("codexsubmcp.cli.scan_npm_global_packages", lambda: [])
    monkeypatch.setattr("codexsubmcp.cli.scan_path_candidates", lambda: [])
    monkeypatch.setattr("codexsubmcp.cli.scan_python_candidates", lambda: [])

    exit_code = main(["scan", "mcp", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert list(payload) == ["configured", "installed_candidates"]
    assert payload["configured"][0]["name"] == "memory"
    assert payload["installed_candidates"] == []
