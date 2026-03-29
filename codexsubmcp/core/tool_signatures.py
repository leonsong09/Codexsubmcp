from __future__ import annotations

from codexsubmcp.core.models import McpRecord


def infer_tool_signature(command_line: str) -> str:
    lowered = command_line.lower()
    patterns = (
        ("chrome-devtools-mcp", "chrome-devtools-mcp"),
        ("chrome_devtools", "chrome-devtools-mcp"),
        ("@playwright/mcp", "playwright-mcp"),
        ("ace-tool", "ace-tool"),
        ("agentation-mcp", "agentation-mcp"),
        ("@modelcontextprotocol/server-memory", "server-memory"),
        ("server-memory", "server-memory"),
        ("@modelcontextprotocol/server-sequential-thinking", "server-sequential-thinking"),
        ("server-sequential-thinking", "server-sequential-thinking"),
        ("mcp-server-fetch", "mcp-server-fetch"),
    )
    for needle, signature in patterns:
        if needle in lowered:
            return signature
    return lowered.strip() or "unknown"


def infer_record_tool_signature(record: McpRecord) -> str:
    haystack = " ".join([record.name, record.command or "", *record.args]).strip()
    return infer_tool_signature(haystack)
