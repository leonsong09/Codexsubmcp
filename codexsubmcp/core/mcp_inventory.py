from __future__ import annotations

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
    }


def build_inventory(
    *,
    configured: list[McpRecord],
    installed_candidates: list[McpRecord],
) -> dict[str, list[dict[str, object]]]:
    return {
        "configured": [record_to_dict(record) for record in sorted(configured, key=lambda item: item.name)],
        "installed_candidates": [
            record_to_dict(record) for record in sorted(installed_candidates, key=lambda item: item.name)
        ],
    }
