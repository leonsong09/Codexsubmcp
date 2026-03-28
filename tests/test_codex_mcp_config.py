from __future__ import annotations

from pathlib import Path

from codexsubmcp.core.codex_mcp_config import (
    discover_codex_config_paths,
    scan_codex_configured_mcps,
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_scan_codex_configured_mcps_reads_global_config(monkeypatch, tmp_path):
    codex_home = tmp_path / ".codex"
    _write(
        codex_home / "config.toml",
        """
        [mcp_servers.memory]
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-memory"]
        """,
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    records = scan_codex_configured_mcps(start_dir=tmp_path / "workspace")

    assert len(records) == 1
    assert records[0].name == "memory"
    assert records[0].source == "codex_global_config"
    assert records[0].command == "npx"
    assert records[0].args == ("-y", "@modelcontextprotocol/server-memory")


def test_discover_codex_config_paths_finds_project_config_upwards(tmp_path):
    project_root = tmp_path / "repo"
    nested_dir = project_root / "packages" / "desktop"
    _write(
        project_root / ".codex" / "config.toml",
        """
        [mcp_servers.playwright]
        command = "npx"
        args = ["-y", "@playwright/mcp"]
        """,
    )

    paths = discover_codex_config_paths(start_dir=nested_dir)
    records = scan_codex_configured_mcps(
        start_dir=nested_dir,
        global_config_path=None,
        project_config_path=paths.project_config_path,
    )

    assert paths.project_config_path == project_root / ".codex" / "config.toml"
    assert len(records) == 1
    assert records[0].source == "codex_project_config"
    assert records[0].name == "playwright"


def test_scan_codex_configured_mcps_normalizes_type_env_and_timeouts(monkeypatch, tmp_path):
    codex_home = tmp_path / ".codex"
    _write(
        codex_home / "config.toml",
        """
        [mcp_servers.fetch]
        command = "uvx"
        args = ["mcp-server-fetch"]
        startup_timeout_ms = 1500
        tool_timeout_sec = 12

        [mcp_servers.fetch.env]
        FETCH_TOKEN = "secret"
        LOG_LEVEL = "debug"

        [mcp_servers.docs]
        url = "https://example.com/mcp"
        tool_timeout_sec = 5.5
        """,
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    records = scan_codex_configured_mcps(start_dir=tmp_path / "workspace")

    fetch = next(record for record in records if record.name == "fetch")
    docs = next(record for record in records if record.name == "docs")

    assert fetch.type == "stdio"
    assert fetch.env_keys == ("FETCH_TOKEN", "LOG_LEVEL")
    assert fetch.startup_timeout_ms == 1500
    assert fetch.tool_timeout_sec == 12.0
    assert docs.type == "streamable_http"
    assert docs.command == "https://example.com/mcp"
    assert docs.tool_timeout_sec == 5.5


def test_scan_codex_configured_mcps_ignores_legacy_json_sources(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData" / "Roaming"
    localappdata = tmp_path / "AppData" / "Local"
    userprofile = tmp_path / "User"
    _write(
        appdata / "Claude" / "claude_desktop_config.json",
        """
        {"mcpServers": {"filesystem": {"command": "npx"}}}
        """,
    )
    _write(
        appdata / "Codex" / "mcp.json",
        """
        {"mcpServers": {"memory": {"command": "npx"}}}
        """,
    )
    _write(
        localappdata / "Codex" / "mcp.json",
        """
        {"mcpServers": {"fetch": {"command": "uvx"}}}
        """,
    )
    _write(
        userprofile / ".cursor" / "mcp.json",
        """
        {"mcpServers": {"playwright": {"command": "npx"}}}
        """,
    )
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("USERPROFILE", str(userprofile))

    paths = discover_codex_config_paths(start_dir=tmp_path / "workspace")
    records = scan_codex_configured_mcps(start_dir=tmp_path / "workspace")

    assert paths.global_config_path is None
    assert paths.project_config_path is None
    assert records == []
