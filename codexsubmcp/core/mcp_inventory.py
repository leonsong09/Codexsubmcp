from __future__ import annotations

from codexsubmcp.core.analysis import RunningMcpSummary
from codexsubmcp.core.models import McpRecord


def record_to_dict(record: McpRecord) -> dict[str, object]:
    return {
        "name": record.name,
        "category": record.category,
        "source": record.source,
        "command": record.command,
        "path": str(record.path) if record.path is not None else None,
        "version": record.version,
        "confidence": record.confidence,
        "notes": record.notes,
        "type": record.type,
        "args": list(record.args),
        "env_keys": list(record.env_keys),
        "startup_timeout_ms": record.startup_timeout_ms,
        "tool_timeout_sec": record.tool_timeout_sec,
    }


def running_to_dict(record: RunningMcpSummary) -> dict[str, object]:
    return {
        "tool_signature": record.tool_signature,
        "instance_count": record.instance_count,
        "live_codex_pid_count": record.live_codex_pid_count,
    }


def build_inventory(
    *,
    configured: list[McpRecord],
    running: list[RunningMcpSummary] | None = None,
    drift: dict[str, object] | None = None,
    installed_candidates: list[McpRecord] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "configured": [record_to_dict(record) for record in sorted(configured, key=lambda item: item.name)]
    }
    if running is not None or drift is not None:
        payload["running"] = [running_to_dict(record) for record in sorted(running or [], key=lambda item: item.tool_signature)]
        payload["drift"] = drift or {
            "configured_not_running": [],
            "running_not_configured": [],
        }
        return payload
    payload["installed_candidates"] = [
        record_to_dict(record) for record in sorted(installed_candidates or [], key=lambda item: item.name)
    ]
    return payload
